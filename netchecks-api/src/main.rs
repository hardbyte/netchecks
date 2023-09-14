
#[macro_use] extern crate rocket;



use rocket::fs::NamedFile;

use k8s_openapi::api::batch::v1::Job;
use kube::{
    api::{Api, DeleteParams, PostParams},
    Client,
    core::crd::CustomResourceExt,
    CustomResource,
    runtime::wait::{await_condition, conditions},
};
use tracing::info;
use garde::Validate;
use serde::{Deserialize, Serialize};
use serde_json::json;
use k8s_openapi::apiextensions_apiserver::pkg::apis::apiextensions::v1::CustomResourceDefinition;
use schemars::JsonSchema;
use crate::network_assertion_rule::{Context, NetworkAssertionRule};

mod network_assertion_rule;

// Own custom resource
#[derive(CustomResource, Deserialize, Serialize, Clone, Debug, Validate, JsonSchema)]
#[kube(group = "netchecks.io", version = "v1", kind = "NetworkAssertion", namespaced)]
#[kube(status = "NetworkAssertionStatus")]
#[kube(printcolumn = r#"{"name":"Team", "jsonPath": ".spec.metadata.team", "type": "string"}"#)]
pub struct NetworkAssertionSpec {
    #[garde(skip)]
    schedule: Option<String>,
    #[garde(skip)]
    disable_redaction: Option<bool>,
    #[garde(skip)]
    context: Option<Vec<Context>>,

    #[garde(skip)]
    rules: Vec<NetworkAssertionRule>,
}



#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
pub struct NetworkAssertionStatusCreation {
    #[serde(rename="job-name")]
    job_name: String,
    #[serde(rename="job-uid")]
    job_uid: String,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
pub struct NetworkAssertionStatus {
    creation: NetworkAssertionStatusCreation
}

#[get("/")]
async fn index() -> String {
    String::from("Hello")
}

#[get("/NetworkAssertions")]
async fn list_network_assertions() -> Option<String> {

    let client = Client::try_default().await.ok()?;

    let crds: Api<CustomResourceDefinition> = Api::all(client.clone());

    // Manage the NetworkAssertion CR
    let nas: Api<NetworkAssertion> = Api::namespaced(client.clone(), "netchecks");
    let first_network_assertion = nas.get("aws-dns-should-work").await.ok()?;


    Some(format!("Hello {:?}", first_network_assertion.metadata.name))
}

#[launch]
fn rocket() -> _ {
    rocket::build().mount("/",
                          routes![index, list_network_assertions])
}
