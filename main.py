import datetime
import json
from collections import defaultdict
from json import JSONDecodeError
from time import sleep
import prometheus_client as prometheus

from kubernetes.client import ApiException, V1ConfigMap, V1ObjectMeta, V1Pod, V1ConfigMapVolumeSource, V1Volume, \
    V1VolumeMount
from structlog import get_logger
from rich import print
import kopf
from kubernetes import client

from netchecksoperator.config import Config


logger = get_logger()
settings = Config()

logger.debug("Starting operator", config=settings.json())
if settings.metrics.enabled:
    prometheus.start_http_server(settings.metrics.port)

VERSION = '0.1.0'
API_GROUP_NAME = "netchecks.io"

# define Prometheus metrics
ASSERTION_COUNT = prometheus.Counter(
    'netchecks_assertions',
    'Number of network assertions',
    ['name']
)
ASSERTION_REQUEST_TIME = prometheus.Summary(
    'netchecks_operator_assertion_processing_seconds',
    'Time spent processing network assertions by the netchecks operator',
    ['name', 'method']
)
ASSERTION_RESULT_TIME = prometheus.Summary('netchecks_operator_assertion_results_processing_seconds',
                                           'Time spent processing network assertion results by the netchecks operator'
                                           )

ASSERTION_TEST_TIME = prometheus.Summary(
    'netchecks_probe_processing_seconds',
    'Time spent testing network assertions by netchecks probe',
    ['name', 'type']
)

@kopf.on.create('networkassertions.v1.netchecks.io')
def creation(body, spec, name, namespace, **kwargs):
    with ASSERTION_REQUEST_TIME.labels(name, 'create').time():
        logger = get_logger(name=name, namespace=namespace)
        batch_v1 = client.BatchV1Api()
        logger.info(f"NetworkAssertion on-create handler called")
        ASSERTION_COUNT.labels(name).inc()

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
        job_spec = create_job_spec(name, cm_response,settings, template_overides=job_template)
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


@kopf.on.update('networkassertions.v1.netchecks.io')
def edit(spec, old, name, namespace, body, **kwargs):
    """
    This is called when someone modifies their NetworkAssertion.

    In the first implementation we just try to delete the Job/CronJob
    and then recreate.

    # https://kopf.readthedocs.io/en/stable/walkthrough/diffs/
    """
    with ASSERTION_REQUEST_TIME.labels(name, 'update').time():
        logger = get_logger(name=name, namespace=namespace)
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

        # TODO: Upsert instead of replace the existing config map
        logger.info("Deleting existing config map")
        core_api = client.CoreV1Api()
        core_api.delete_namespaced_config_map(
            name=name,
            namespace=namespace,
        )
        logger.info("Removed existing config map")


        logger.info("Recreating resources")
        creation(body=body, spec=spec, name=name, namespace=namespace)


@kopf.on.delete('networkassertions.v1.netchecks.io')
def delete(name, namespace, **kwargs):
    logger = get_logger(name=name, namespace=namespace)
    logger.info(f"networkassertion delete handler called")


@kopf.on.resume('networkassertions.v1.netchecks.io')
def on_resume(spec, name, namespace, **kwargs):
    logger = get_logger(name=name, namespace=namespace)
    logger.info(f"networkassertions resume handler called")

    # May need to explicitly restart daemon?


@kopf.daemon('pod',
             labels={
                 'app.kubernetes.io/name': 'netchecks',
                 'app.kubernetes.io/component': 'probe'
             },
             )
@ASSERTION_RESULT_TIME.time()
def monitor_selected_netcheck_pods(name, namespace, spec, status, stopped, **kwargs):
    logger = get_logger(name=name, namespace=namespace)
    logger.info("Monitoring pod")
    core_v1 = client.api.core_v1_api.CoreV1Api()

    while not stopped:
        logger.debug("Getting pod status")
        pod: V1Pod = core_v1.read_namespaced_pod(name=name, namespace=namespace)

        assertion_name = pod.metadata.labels['app.kubernetes.io/instance']
        logger = logger.bind(assertion_name=assertion_name)

        match pod.status.phase:
            case 'Pending':
                # While Pod is still pending just wait
                logger.info("Waiting for pod to start")
                sleep(5)
                continue
            case 'Succeeded':
                # Note it is possible to get here having already processed this container
                # (e.g. after operator restart)
                logger.info("Probe Pod has completed")
                logger.info("Getting pod output")
                # Doesn't seem to be a nice way to separate stdout and stderr
                pod_log_ws_client = core_v1.read_namespaced_pod_log(name=name, namespace=namespace, _preload_content=False)
                #pod_log_ws_client.run_forever(timeout=10)
                pod_log = pod_log_ws_client.data.decode('utf-8')
                logger.debug("Pod Log", log=pod_log)
                if pod_log.startswith('unable to retrieve container logs'):
                    logger.warning("Unable to retrieve container logs.")
                    return

                # Process the results, creating or updating the associated PolicyReport

                process_probe_output(pod_log, assertion_name, namespace, name)

                break
            case _:
                logger.info("Pod details retrieved", phase=pod.status.phase, status=pod.status)
                sleep(1.0)
    logger.info("Pod monitoring complete", name=name, namespace=namespace)


def summarize_results(probe_results):
    """
    Summarize the results of the probe run
    """
    logger = get_logger()
    logger.info("Summarizing probe results", probe_results=probe_results)
    # Dict of pass/fail/warn/error counts defaulting to 0
    summary = defaultdict(int)

    for assertion_detail in probe_results['assertions']:
        for test_result in assertion_detail['results']:
            # Each individual assertion's test result is a dict with a 'status' key that should
            # be one of: pass, fail, warn, error, skip
            summary[test_result.get('status', 'skip')] += 1

    return summary


def convert_results_for_policy_report(probe_results, namespace, pod_name):
    # https://htmlpreview.github.io/?https://github.com/kubernetes-sigs/wg-policy-prototypes/blob/master/policy-report/docs/index.html
    res = []
    logger = get_logger()
    for assertion_result in probe_results['assertions']:
        for i, test_result in enumerate(assertion_result['results'], start=1):
            policy_report_data = {
                'spec': json.dumps(test_result['spec']),
                'data': json.dumps(test_result['data'])
            }

            test_result_iso_timestamp = test_result['data']['endTimestamp']
            policy_report_result = {
                "source": "netchecks",
                "policy": assertion_result['name'],
                "rule": test_result.get('name', f"{assertion_result['name']}-rule-{i}"),
                "category": test_result['spec']['type'],    # This is the test type: http/dns
                # "severity": test_result.get('severity'),   # high, medium, low
                "timestamp": convert_iso_timestamp_to_k8s_timestamp(test_result_iso_timestamp),
                "result": test_result.get('status', 'skip'),
                #"scored": True,

                "message": test_result.get('message', f'Rule from {assertion_result["name"]}'),
                # Properties have to be str -> str
                "properties": policy_report_data,

                # "resources": [
                #     {
                #         "name": pod_name,
                #         "namespace": namespace,
                #         "kind": "Pod",
                #         "apiVersion": "v1",
                #     }
                # ],
            }
            logger.info("Policy Report Result", policy_report_result=policy_report_result)
            res.append(policy_report_result)
    return res


def convert_iso_timestamp_to_k8s_timestamp(iso_timestamp):
    # Convert ISO timestamp to Kubernetes meta/v1.Timestamp format
    return {
        "nanos": 0,
        "seconds": int(datetime.datetime.fromisoformat(iso_timestamp).timestamp())
    }


def upsert_policy_report(probe_results, nework_assertion_name, namespace, pod_name):
    crd_api = client.CustomObjectsApi()

    logger = get_logger(name=nework_assertion_name, namespace=namespace, pod_name=pod_name)
    logger.info("Upsert PolicyReport")
    # TODO Use the Pod name to record in the PolicyReport result
    # get the resource and print out data

    # If it doesn't exist, create it
    policy_report_label_selector = f"app.kubernetes.io/instance={nework_assertion_name}"
    policy_reports = crd_api.list_namespaced_custom_object(
        group='wgpolicyk8s.io',
        version="v1alpha2",
        namespace=namespace,
        plural="policyreports",
        label_selector=policy_report_label_selector,
    )
    labels = get_common_labels(name=nework_assertion_name)
    labels['policy.kubernetes.io/engine'] = 'netcheck'
    report_results = convert_results_for_policy_report(probe_results, namespace, pod_name)
    report_summary = summarize_results(probe_results)
    policy_report_body = {
        "apiVersion": "wgpolicyk8s.io/v1alpha2",
        "kind": "PolicyReport",
        "scope": {"kind": "Namespace", "name": namespace, "apiGroup": "v1"},
        "metadata": {
            "name": nework_assertion_name,
            "labels": labels,
            "annotations": {
                "category": "Network",
                "created-by": "netcheck",
                "netcheck-operator-version": VERSION
            }
        },
        "results": report_results,
        "summary": report_summary
    }

    if len(policy_reports['items']) > 0:
        logger.info("Existing policy reports found", reports=policy_reports)
        policy_report = crd_api.get_namespaced_custom_object(
            group='wgpolicyk8s.io',
            version="v1alpha2",
            namespace=namespace,
            plural="policyreports",
            name=nework_assertion_name,
        )
        logger.info("Existing policy report found", report=policy_report)
        crd_api.patch_namespaced_custom_object(
            group='wgpolicyk8s.io',
            version="v1alpha2",
            namespace=namespace,
            plural="policyreports",
            body=policy_report_body,
            name=nework_assertion_name,
        )
        logger.info("Updated existing PolicyReport")
    else:
        # Create a new PolicyReport
        logger.info("Creating new PolicyReport")

        kopf.adopt(policy_report_body)
        try:
            policy_report = crd_api.create_namespaced_custom_object(
                group='wgpolicyk8s.io',
                version="v1alpha2",
                namespace=namespace,
                plural="policyreports",
                body=policy_report_body
            )
        except ApiException as e:
            logger.error("Failed to create PolicyReport", status=e.status, error=e)
            raise

        logger.info("PolicyReport created", policy_report=policy_report)

    return policy_report


def process_probe_output(pod_log: str, network_assertion_name, namespace, pod_name):
    """
    Extract JSON from pod log
    """
    try:
        probe_results = json.loads(pod_log)
    except JSONDecodeError as e:
        print("Error parsing output from probe pod as JSON.\n\n", pod_log)
        raise e

    print("Probe results", probe_results)
    upsert_policy_report(probe_results, network_assertion_name, namespace, pod_name)

    # Update prometheus metrics for the probe results

    for assertion_result in probe_results['assertions']:
        for test_result in assertion_result['results']:
            test_start_iso_timestamp = datetime.datetime.fromisoformat(test_result['data']['startTimestamp'])
            test_end_iso_timestamp = datetime.datetime.fromisoformat(test_result['data']['endTimestamp'])
            test_duration = (test_end_iso_timestamp - test_start_iso_timestamp).total_seconds()

            ASSERTION_TEST_TIME.labels(name=network_assertion_name, type=test_result['spec']['type']).observe(test_duration)


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
        'app.kubernetes.io/name': 'netchecks',
        'app.kubernetes.io/version': VERSION,
        'app.kubernetes.io/instance': name
    }


def create_job_spec(name, cm: V1ConfigMap, settings: Config, template_overides: dict = None):
    # Container template first
    container = client.V1Container(
        name="netcheck",
        # e.g "ghcr.io/netchecks/netchecks:main"
        image=f"{settings.probe.image.repository}:{settings.probe.image.tag}",
        image_pull_policy=settings.probe.image.pullPolicy,
        command=["poetry", "run", "netcheck", "run", "--config", "/netcheck/rules.json"],
        volume_mounts=[
            V1VolumeMount(name='netcheck-rules', mount_path='/netcheck')
        ],
        env=[
            # V1EnvVar(name="NETCHECK_CONFIG", value="/netcheck/")
        ]
    )
    # Create and configure a pod spec section
    labels = get_common_labels(name)
    labels['app.kubernetes.io/component'] = 'probe'
    pod_template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels=labels,
            annotations=settings.probe.podAnnotations
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

