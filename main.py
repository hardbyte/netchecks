from kubernetes.client import V1Job
from structlog import wrap_logger
from rich import print
import kopf
from kubernetes import client, config



@kopf.on.create('networkassertions')
async def creation(body, spec, name, namespace, logger, **kwargs):
    logger = wrap_logger(logger)
    logger.info(f"networkassertion creation handler called", name=name, namespace=namespace)

    logger.debug(f"Requested NetworkAssertion body", body=body)
    logger.info(f"Requested NetworkAssertion spec", spec=spec)

    # Validate the NetworkAssertion spec
    rules = spec.get('rules')
    if not rules:
        raise kopf.PermanentError(f"Rules must be set.")

    logger.info("Creating a Job")
    batch_v1 = client.BatchV1Api()
    # Create a job object with client-python API. The job we
    # created is same as the `pi-job.yaml` in the /examples folder.
    job_name = f"{name}"
    job = create_job_object(job_name)
    logger.debug("Job spec created", job=job)

    logger.info("Linking job with NetworkAssertion")
    kopf.adopt(job)

    api_response = create_job(batch_v1, job)
    logger.info("Pushed job object to k8s api", response=api_response)
    logger.info("Job created", status=api_response.status)

    # logger.info("Sleeping before checking status")
    # sleep(3)
    # logger.info("Checking job status")
    # get_job_status(batch_v1, job_name)

    # Note the response gets attached to the NetworkAssertion `status.creation`
    return {
        "job-name": api_response.metadata.name,
        "job-uid": api_response.metadata.uid
    }


@kopf.on.update('networkassertions')
def edit(spec, old, new, name, namespace, logger, **kwargs):
    logger = wrap_logger(logger)
    logger.info(f"networkassertion mutation handler called", name=name, namespace=namespace)
    logger.info("Spec", spec=spec)
    logger.info("Compare", old=old, new=new)


@kopf.on.delete('networkassertions')
def delete(name, namespace, logger, **kwargs):
    logger = wrap_logger(logger)
    logger.info(f"networkassertion delete handler called", name=name, namespace=namespace)


@kopf.on.resume('networkassertions')
def delete(spec, name, namespace, logger, **kwargs):
    logger = wrap_logger(logger)
    logger.info(f"networkassertion resume handler called", name=name, namespace=namespace)

    # Start daemon thread



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


def create_job_object(job_name: str):
    # Container template first
    container = client.V1Container(
        name="pi",
        image="perl",
        command=["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"])

    # Create and configure a pod spec section
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": "pi"}),
        spec=client.V1PodSpec(restart_policy="Never", containers=[container])
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


