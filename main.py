import json
from time import sleep

from kubernetes.client import V1ConfigMap, V1ObjectMeta, V1Pod, V1ConfigMapVolumeSource, V1Volume, \
    V1VolumeMount
from structlog import get_logger
from rich import print
import kopf
from kubernetes import client

VERSION = '0.1.0'


@kopf.on.create('networkassertions')
def creation(body, spec, name, namespace, **kwargs):
    logger = get_logger()
    logger.info(f"NetworkAssertion on-create handler called", name=name, namespace=namespace)

    batch_v1 = client.BatchV1Api()
    logger.debug(f"Requested NetworkAssertion body", body=body)
    logger.info(f"Requested NetworkAssertion spec", spec=spec)

    # Validate the NetworkAssertion spec
    rules = spec.get('rules')
    logger.info("Rules loaded from NetworkAssertion", rules=rules)
    if not rules:
        raise kopf.PermanentError(f"Rules must be set.")

    # Grab any template overrides (metadata, spec->serviceAccountName)
    job_template = spec.get('template')

    cm_response = create_network_assertions_config_map(name, rules, namespace, logger)

    # Create a job spec
    job_spec = create_job_spec(name, cm_response, template_overides=job_template)
    logger.debug("Job spec created", job_spec=job_spec)
    job = create_job_object(name, job_spec)
    logger.debug("Job instance created", job=job)

    schedule = spec.get('schedule')
    if schedule is not None:
        logger.info("Schedule defined. Creating CronJob", schedule=schedule)
        # Create a CronJob

        cron_job_spec = client.V1CronJobSpec(
            job_template=job,
            schedule=schedule
        )

        cron_job = client.V1CronJob(
            api_version="batch/v1",
            kind="CronJob",
            metadata=client.V1ObjectMeta(name=name),
            spec=cron_job_spec
        )
        logger.info("Creating CronJob in k8s")
        logger.debug("Linking CronJob with NetworkAssertion")
        kopf.adopt(cron_job)
        api_response = batch_v1.create_namespaced_cron_job(body=cron_job, namespace=namespace)
        # Attach an event to the NetworkAssertion (visible with `kubectl describe networkassertion/xyz`)
        kopf.info(body, reason="CronJobCreated",
                  message=f"CronJob '{api_response.metadata.name}' created to carry out check.")

    else:
        logger.info("Creating a Job")
        logger.debug("Linking job with NetworkAssertion")
        kopf.adopt(job)
        api_response = batch_v1.create_namespaced_job(body=job, namespace=namespace)
        logger.info("Pushed job object to k8s api")
        # Attach an event to the NetworkAssertion (visible with `kubectl describe networkassertion/xyz`)
        kopf.info(body, reason="JobCreated",
                  message=f"Job '{api_response.metadata.name}' created to carry out check.")

    # Note the returned data gets attached to the NetworkAssertion `status.creation`
    return {
        "job-name": api_response.metadata.name,
        "job-uid": api_response.metadata.uid
    }


def create_network_assertions_config_map(name, rules, namespace, logger):
    core_api = client.CoreV1Api()

    # This will inherit the name of the network assertion
    config_map = V1ConfigMap(
        metadata=V1ObjectMeta(labels=get_common_labels(name)),
        data={
            # This gets mounted at /netcheck/rules.json
            # For now we create one "Assertion", with all the rules
            # from the NetworkAssertion
            "rules.json": json.dumps({
                "assertions": [
                    {"name": r['name'], "rules": [r]} for r in rules
                ]
            })
        }
    )
    kopf.adopt(config_map)
    logger.info("Creating config map")
    logger.debug("Config map spec", cm=config_map)
    cm_response = core_api.create_namespaced_config_map(
        namespace=namespace,
        body=config_map
    )
    logger.info("Created config map")
    logger.debug("K8s response to creating config map", cm=cm_response)
    return cm_response


@kopf.on.update('networkassertions')
def edit(spec, old, name, namespace, body, **kwargs):
    """
    This is called when someone modifies their NetworkAssertion.

    In the first implementation we just try to delete the Job/CronJob
    and then recreate.

    # https://kopf.readthedocs.io/en/stable/walkthrough/diffs/
    """
    logger = get_logger()
    logger.info(f"Mutation handler called", name=name, namespace=namespace)
    logger.info("Spec", spec=spec)
    logger.info("Old", old=old)
    logger.info("Diff", diff=kwargs.get('diff'))

    logger.info("Trying to find associated Job/CronJob")
    batch_v1 = client.BatchV1Api()

    if 'schedule' in old['spec']:
        logger.info("Deleting CronJob")
        try:
            batch_v1.delete_namespaced_cron_job(name=name, namespace=namespace)
        except client.exceptions.ApiException as e:
            logger.info("Couldn't find existing CronJob. Ignoring", exc_info=e)
    else:
        logger.info("Deleting Job")
        try:
            batch_v1.delete_namespaced_job(name=name, namespace=namespace)
        except client.exceptions.ApiException as e:
            logger.info("Couldn't find existing Job. Ignoring", exc_info=e)

    logger.info("Recreating resources")
    creation(body=body, spec=spec, name=name, namespace=namespace)


@kopf.on.delete('networkassertions')
def delete(name, namespace, **kwargs):
    logger = get_logger()
    logger.info(f"networkassertion delete handler called", name=name, namespace=namespace)


@kopf.on.resume('networkassertions')
def on_resume(spec, name, namespace, **kwargs):
    logger = get_logger()
    logger.info(f"networkassertions resume handler called", name=name, namespace=namespace)

    # May need to explicitly restart daemon?


@kopf.daemon('pod',
             #annotations={'some-annotation': 'some-value'},
             labels={'app': 'netcheck'},
             #when=lambda name, **_: 'some' in name
             )
def monitor_selected_netcheck_pods(name, namespace, spec, status, stopped, **kwargs):
    logger = get_logger()
    logger.info("Monitoring pod", name=name, namespace=namespace)
    core_v1 = client.api.core_v1_api.CoreV1Api()

    while not stopped:
        logger.debug("Getting pod status", name=name, namespace=namespace)
        pod: V1Pod = core_v1.read_namespaced_pod(name=name, namespace=namespace)

        match pod.status.phase:
            case 'Pending':
                # While Pod is still pending just wait
                logger.info("Waiting for pod to start")
                sleep(5)
                continue
            case 'Succeeded':
                logger.info("Succeeded")
                logger.info("Getting pod output")
                # Doesn't seem to be a nice way to separate stdout and stderr
                pod_log = core_v1.read_namespaced_pod_log(name=name, namespace=namespace)
                logger.info("Pod Log", log=pod_log, name=name, namespace=namespace)
                # Process the results, create or update PolicyReport


                break
            case _:
                logger.info("Pod details retrieved", phase=pod.status.phase, status=pod.status)
                sleep(1.0)
    logger.info("Pod monitoring complete", name=name, namespace=namespace)


def get_job_status(api_instance, job_name):
    api_response = api_instance.read_namespaced_job_status(
        name=job_name,
        namespace="default")

    job_completed = api_response.status.succeeded is not None or \
                api_response.status.failed is not None

    print(f"Job status='{api_response.status}'")
    print(f"Job completed={job_completed}")
    return job_completed, api_response.status


def create_job_object(job_name: str, job_spec):
    # Instantiate the job object
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=job_name),
        spec=job_spec)

    return job


def get_common_labels(name):
    return {
        'app.kubernetes.io/name': 'netcheck',
        'app.kubernetes.io/component': 'probe',
        'app.kubernetes.io/version': VERSION,
        'app.kubernetes.io/instance': name
    }


def create_job_spec(name, cm: V1ConfigMap, template_overides: dict = None):
    # Container template first
    container = client.V1Container(
        name="netcheck",
        image="ghcr.io/hardbyte/netcheck:main",
        image_pull_policy="Always",  # Until we pin versions
        command=["poetry", "run", "netcheck", "run", "--config", "/netcheck/rules.json"],
        volume_mounts=[
            V1VolumeMount(name='netcheck-rules', mount_path='/netcheck')
        ],
        env=[
            # V1EnvVar(name="NETCHECK_CONFIG", value="/netcheck/")
        ]
    )
    # Create and configure a pod spec section
    pod_template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels=get_common_labels(name),
            annotations={}
        ),
        spec=client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=[
                V1Volume(
                    name='netcheck-rules',
                    config_map=V1ConfigMapVolumeSource(name=cm.metadata.name)
                )
            ]
        )
    )

    if template_overides:
        print("Applying template overrides", template_overides)
        pod_template = apply_overrides(pod_template, template_overides)

        print(pod_template)
        #pod_template = client.V1PodTemplateSpec(**overridden_pod_template_dict)

    # Create the specification of the job
    spec = client.V1JobSpec(
        template=pod_template,
        backoff_limit=4
    )

    return spec


def apply_overrides(template, overrides: dict):
    # This is a bit of a hack to apply overrides to the pod template
    def _apply_overrides(obj, overrides: dict):
        for k, v in overrides.items():
            key = k
            # k will be in camelCase (as it appears in Kubernetes manifests e.g., serviceAccountName)
            if hasattr(obj, 'attribute_map'):
                # reverse the dict obj.attribute_map because the kubernetes python client
                # expects attributes named with snake_case.
                reverse_map = {v: k for k, v in obj.attribute_map.items()}
                key = reverse_map.get(k, k)

            if hasattr(obj, key):
                if getattr(obj, key) is None:
                    setattr(obj, key, {})
                if isinstance(v, dict):
                    _apply_overrides(getattr(obj, key), v)
                else:
                    setattr(obj, key, v)
            else:
                try:
                    obj[key] = v
                except TypeError:
                    setattr(obj, key, v)

    _apply_overrides(template, overrides)
    return template

# def main():
#     config.load_kube_config()
#
#     api = client.CustomObjectsApi()
#
#     # it's my custom resource defined as Dict
#     my_resource = {
#         "apiVersion": "stable.example.com/v1",
#         "kind": "CronTab",
#         "metadata": {"name": "my-new-cron-object"},
#         "spec": {
#             "cronSpec": "* * * * */5",
#             "image": "my-awesome-cron-image"
#         }
#     }
#
#     # patch to update the `spec.cronSpec` field
#     patch_body = {
#         "spec": {"cronSpec": "* * * * */10", "image": "my-awesome-cron-image"}
#     }
#
#     # create the resource
#     api.create_namespaced_custom_object(
#         group="stable.example.com",
#         version="v1",
#         namespace="default",
#         plural="crontabs",
#         body=my_resource,
#     )
#     print("Resource created")
#
#     # get the resource and print out data
#     resource = api.get_namespaced_custom_object(
#         group="stable.example.com",
#         version="v1",
#         name="my-new-cron-object",
#         namespace="default",
#         plural="crontabs",
#     )
#     print("Resource details:")
#     pprint(resource)
#
#     # patch the namespaced custom object to update the `spec.cronSpec` field
#     patch_resource = api.patch_namespaced_custom_object(
#         group="stable.example.com",
#         version="v1",
#         name="my-new-cron-object",
#         namespace="default",
#         plural="crontabs",
#         body=patch_body,
#     )
#     print("Resource details:")
#     pprint(patch_resource)
#
#     # delete it
#     api.delete_namespaced_custom_object(
#         group="stable.example.com",
#         version="v1",
#         name="my-new-cron-object",
#         namespace="default",
#         plural="crontabs",
#         body=client.V1DeleteOptions(),
#     )
#     print("Resource deleted")

