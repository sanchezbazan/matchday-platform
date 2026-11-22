# --- Who may invoke the Lambda: EventBridge Scheduler, from this account only ---

data "aws_iam_policy_document" "assume_scheduler" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.function_name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.assume_scheduler.json
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.ingestion.arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "${local.function_name}-scheduler"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}

# --- The two schedules ---

resource "aws_scheduler_schedule" "live" {
  name                = "${local.function_name}-live"
  schedule_expression = "rate(5 minutes)"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.ingestion.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ mode = "live" })

    retry_policy {
      maximum_retry_attempts = 0
    }
  }
}

resource "aws_scheduler_schedule" "fixtures" {
  name                = "${local.function_name}-fixtures"
  schedule_expression = "cron(0 9 * * ? *)"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.ingestion.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ mode = "fixtures" })

    retry_policy {
      maximum_retry_attempts = 2
    }
  }
}

# --- Don't let Lambda retry failed runs on its own ---

resource "aws_lambda_function_event_invoke_config" "ingestion" {
  function_name          = aws_lambda_function.ingestion.function_name
  maximum_retry_attempts = 0
}