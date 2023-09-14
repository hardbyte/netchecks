use garde::Validate;
use serde::{Deserialize, Serialize};
use serde_json::json;
use schemars::JsonSchema;


#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
pub struct RuleValidation {
    message: String,
    pattern: Option<String>,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
pub struct Context {
    name: String,
    config_map: Option<ConfigMap>,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
pub struct ConfigMap {
    name: String,
}

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
pub enum RuleType {
    http,
    dns,
}

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
pub enum ExpectedResult {
    pass,
    fail,
}

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
pub struct NetworkAssertionRule {
    name: String,
    #[serde(rename = "type")]
    rule_type: RuleType,
    url: Option<String>,
    server: Option<String>,
    host: Option<String>,
    expected: Option<ExpectedResult>,
    headers: Option<std::collections::HashMap<String, String>>,
    validate: Option<RuleValidation>,
}
