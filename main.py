import json
from time import sleep

from kubernetes.client import V1ConfigMap, V1Job, V1ObjectMeta, V1Pod, V1ConfigMapVolumeSource, V1Volume, \
    V1VolumeMount
from structlog import get_logger
from rich import print
import kopf
from kubernetes import client


@kopf.on.create('networkassertions')
async def creation(body, spec, name, namespace, **kwargs):
    logger = get_logger()
    logger.info(f"NetworkAssertion on-create handler called", name=name, namespace=namespace)
    core_api = client.CoreV1Api()
    batch_v1 = client.BatchV1Api()
    logger.debug(f"Requested NetworkAssertion body", body=body)
    logger.info(f"Requested NetworkAssertion spec", spec=spec)

    # Validate the NetworkAssertion spec
    rules = spec.get('rules')
    logger.info("Rules loaded from NetworkAssertion", rules=rules)
    if not rules:
        raise kopf.PermanentError(f"Rules must be set.")

    # TODO check if CM already exists
    config_map = V1ConfigMap(
        metadata=V1ObjectMeta(labels={'hardbyte.nz/netcheck-config': 'true'}),
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
    logger.info("Creating config map", cm=config_map)
    cm_response = core_api.create_namespaced_config_map(
        namespace=namespace,
        body=config_map
    )
    logger.info("Created config map", cm=cm_response)

    logger.info("Creating a Job")

    # Create a job object with client-python API. The job we
    # created is same as the `pi-job.yaml` in the /examples folder.
    job_name = f"{name}"
    job = create_job_object(job_name, cm_response)
    logger.debug("Job spec created", job=job)

    logger.info("Linking job with NetworkAssertion")
    kopf.adopt(job)

    api_response = create_job(batch_v1, job)
    logger.info("Pushed job object to k8s api")
    logger.debug("Job created", uid=api_response.metadata.uid)
    # Attach an event (visible with `kubectl describe`)
    kopf.info(body, reason="JobCreated",
              message=f"Job '{api_response.metadata.name}' created to carry out check.")

    # Note the returned data gets attached to the NetworkAssertion `status.creation`
    return {
        "job-name": api_response.metadata.name,
        "job-uid": api_response.metadata.uid
    }


@kopf.on.update('networkassertions')
def edit(spec, old, new, name, namespace, **kwargs):
    logger = get_logger()
    logger.info(f"networkassertion mutation handler called", name=name, namespace=namespace)
    logger.info("Spec", spec=spec)
    logger.info("Compare", old=old, new=new)


@kopf.on.delete('networkassertions')
def delete(name, namespace, **kwargs):
    logger = get_logger()
    logger.info(f"networkassertion delete handler called", name=name, namespace=namespace)


@kopf.on.resume('networkassertions')
def on_resume(spec, name, namespace, **kwargs):
    logger = get_logger()
    logger.info(f"networkassertion resume handler called", name=name, namespace=namespace)

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


def create_job(api_instance, job: V1Job):
    api_response = api_instance.create_namespaced_job(
        body=job,
        namespace="default")

    return api_response


def create_job_object(job_name: str, cm: V1ConfigMap):
    # Container template first
    container = client.V1Container(
        name="netcheck",
        image="ghcr.io/hardbyte/netcheck:main",
        image_pull_policy="Always", # Until we pin versions
        #command=["cat", "/netcheck/rules.json"],
        command=["poetry", "run", "netcheck", "run", "--config", "/netcheck/rules.json"],
        volume_mounts=[
            V1VolumeMount(name='netcheck-rules', mount_path='/netcheck')
        ],
        env=[
            #V1EnvVar(name="NETCHECK_CONFIG", value="/netcheck/")
        ]
    )

    # Create and configure a pod spec section
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels={"app": "netcheck"},
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

    # Create the specification of the job
    spec = client.V1JobSpec(
        template=template,
        backoff_limit=4
    )
    # Instantiate the job object
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=job_name),
        spec=spec)

    return job


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

