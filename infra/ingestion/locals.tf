data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  function_name = "matchday-ingestion"
  account_id    = data.aws_caller_identity.current.account_id
  region        = data.aws_region.current.region
}