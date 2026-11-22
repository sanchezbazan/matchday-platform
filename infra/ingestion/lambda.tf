data "archive_file" "ingestion" {
  type        = "zip"
  source_dir  = "${path.module}/../../services/ingestion/build"
  output_path = "${path.module}/ingestion.zip"
}

resource "aws_cloudwatch_log_group" "ingestion" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 14
}

resource "aws_lambda_function" "ingestion" {
  function_name    = local.function_name
  role             = aws_iam_role.ingestion.arn
  runtime          = "python3.14"
  architectures    = ["arm64"]
  handler          = "handler.handler"
  filename         = data.archive_file.ingestion.output_path
  source_code_hash = data.archive_file.ingestion.output_base64sha256
  memory_size      = 256
  timeout          = 120

  environment {
    variables = {
      DATABASE_URL_PARAM = "/matchday/database-url"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.ingestion,
    aws_iam_role_policy.ingestion,
  ]
}