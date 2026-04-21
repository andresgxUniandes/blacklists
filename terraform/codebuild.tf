# ── IAM Role for CodeBuild ────────────────────────────────────────────────────

resource "aws_iam_role" "codebuild" {
  name = "${local.name_prefix}-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "codebuild.amazonaws.com" }
    }]
  })

  tags = merge(local.tags, { Name = "${local.name_prefix}-codebuild-role" })
}

resource "aws_iam_role_policy" "codebuild" {
  name = "${local.name_prefix}-codebuild-policy"
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/codebuild/${local.name_prefix}-build*"
      },
      {
        Sid    = "S3AppBundle"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:GetBucketAcl",
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.app_bundle.arn,
          "${aws_s3_bucket.app_bundle.arn}/*"
        ]
      },
      {
        Sid    = "ElasticBeanstalkDeploy"
        Effect = "Allow"
        Action = [
          "elasticbeanstalk:CreateApplicationVersion",
          "elasticbeanstalk:UpdateEnvironment",
          "elasticbeanstalk:DescribeEnvironments",
          "elasticbeanstalk:DescribeApplicationVersions",
          "elasticbeanstalk:DescribeEvents"
        ]
        Resource = "*"
      },
      {
        Sid    = "CodeBuildReports"
        Effect = "Allow"
        Action = [
          "codebuild:CreateReportGroup",
          "codebuild:CreateReport",
          "codebuild:UpdateReport",
          "codebuild:BatchPutTestCases"
        ]
        Resource = "arn:aws:codebuild:${var.aws_region}:*:report-group/${local.name_prefix}-build*"
      }
    ]
  })
}

# ── CodeBuild Project ─────────────────────────────────────────────────────────

resource "aws_codebuild_project" "blacklist" {
  name          = "${local.name_prefix}-build"
  description   = "Build, test, and deploy the Blacklist application to Elastic Beanstalk"
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = 20

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:7.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "S3_BUCKET"
      value = aws_s3_bucket.app_bundle.id
    }

    environment_variable {
      name  = "EB_APP_NAME"
      value = aws_elastic_beanstalk_application.blacklist.name
    }

    environment_variable {
      name  = "EB_ENV_NAME"
      value = aws_elastic_beanstalk_environment.blacklist.name
    }

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }
  }

  source {
    type            = "GITHUB"
    location        = var.github_repo_url
    git_clone_depth = 1

    git_submodules_config {
      fetch_submodules = false
    }
  }

  source_version = "main"

  logs_config {
    cloudwatch_logs {
      group_name  = "/aws/codebuild/${local.name_prefix}-build"
      stream_name = "build-log"
    }
  }

  tags = merge(local.tags, { Name = "${local.name_prefix}-build" })
}
