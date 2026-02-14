"""AWS Lambda handler for LlmEval."""
import os
import sys
import json
import logging
import boto3
from pathlib import Path

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add parent directory to path for imports
sys.path.insert(0, '/var/task')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def download_db_from_s3(bucket_name, db_file='/tmp/releases.db'):
    """Download database from S3 if it exists."""
    if not bucket_name:
        logger.info("No S3 bucket configured, using empty database")
        return False

    try:
        s3 = boto3.client('s3')
        s3.download_file(bucket_name, 'releases.db', db_file)
        logger.info(f"Downloaded database from s3://{bucket_name}/releases.db")
        return True
    except s3.exceptions.NoSuchKey:
        logger.info("No existing database in S3, will create new one")
        return False
    except Exception as e:
        logger.warning(f"Could not download database from S3: {e}")
        return False


def upload_db_to_s3(bucket_name, db_file='/tmp/releases.db'):
    """Upload database to S3 after processing."""
    if not bucket_name:
        logger.warning("No S3 bucket configured, database not persisted!")
        return False

    try:
        s3 = boto3.client('s3')
        s3.upload_file(db_file, bucket_name, 'releases.db')
        logger.info(f"Uploaded database to s3://{bucket_name}/releases.db")

        # Also upload a timestamped backup
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_key = f'backups/releases_{timestamp}.db'
        s3.upload_file(db_file, bucket_name, backup_key)
        logger.info(f"Backup saved to s3://{bucket_name}/{backup_key}")

        return True
    except Exception as e:
        logger.error(f"Failed to upload database to S3: {e}")
        return False


def lambda_handler(event, context):
    """
    AWS Lambda entry point for LlmEval.

    Environment Variables Required:
    - DISCORD_WEBHOOK_URL: Discord webhook for notifications
    - OPENROUTER_API_KEY: OpenRouter API key for LLM
    - S3_BUCKET_NAME: S3 bucket for database storage (optional but recommended)
    - HUGGINGFACE_TOKEN: HuggingFace token (optional)
    - KAGGLE_USERNAME: Kaggle username (optional)
    - KAGGLE_KEY: Kaggle API key (optional)
    - GITHUB_TOKEN: GitHub token (optional)
    """
    logger.info("=" * 60)
    logger.info("LlmEval Lambda Function Starting")
    logger.info(f"Request ID: {context.request_id}")
    logger.info(f"Memory Limit: {context.memory_limit_in_mb} MB")
    logger.info(f"Time Remaining: {context.get_remaining_time_in_millis()} ms")
    logger.info("=" * 60)

    # Get S3 bucket name
    s3_bucket = os.environ.get('S3_BUCKET_NAME', '')

    try:
        # Setup database path in /tmp (only writable directory in Lambda)
        db_path = '/tmp/releases.db'
        os.environ['DATABASE_PATH'] = db_path

        # Download existing database from S3
        if s3_bucket:
            download_db_from_s3(s3_bucket, db_path)
        else:
            logger.warning("⚠️  No S3_BUCKET_NAME configured! Database won't persist between runs!")

        # Create config file in /tmp
        config_path = '/tmp/config.yaml'
        create_lambda_config(config_path)

        # Import and run monitor
        from src.main import ReleaseMonitor

        logger.info("Initializing ReleaseMonitor...")
        monitor = ReleaseMonitor(config_path)

        logger.info("Running monitor cycle...")
        monitor.run()

        # Upload database back to S3
        if s3_bucket:
            upload_db_to_s3(s3_bucket, db_path)

        # Get statistics
        from src.database import ReleaseDatabase
        db = ReleaseDatabase(db_path)
        stats = db.get_stats()

        logger.info("=" * 60)
        logger.info("LlmEval Lambda Function Completed Successfully")
        logger.info(f"Total releases tracked: {stats['total']}")
        logger.info(f"Passed filter: {stats['passed_filter']}")
        logger.info(f"Sent to Discord: {stats['sent']}")
        logger.info("=" * 60)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'LlmEval completed successfully',
                'stats': stats,
                'request_id': context.request_id
            })
        }

    except Exception as e:
        logger.error("=" * 60)
        logger.error("ERROR in Lambda Function")
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 60)
        logger.exception("Full traceback:")

        # Try to upload database even on error
        if s3_bucket and os.path.exists('/tmp/releases.db'):
            try:
                upload_db_to_s3(s3_bucket, '/tmp/releases.db')
            except:
                pass

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'LlmEval failed',
                'error': str(e),
                'request_id': context.request_id
            })
        }


def create_lambda_config(config_path):
    """Create config.yaml in /tmp with environment variables."""

    config_content = f"""# LlmEval Configuration for AWS Lambda
# Auto-generated from environment variables

schedule:
  cron: "0 9,21 * * *"

discord:
  webhook_url: "{os.environ.get('DISCORD_WEBHOOK_URL', '')}"
  dry_run: false

llm:
  provider: "openrouter"
  api_key: "{os.environ.get('OPENROUTER_API_KEY', '')}"
  model: "deepseek/deepseek-chat"
  temperature: 0.3

platforms:
  huggingface:
    enabled: true
    check_models: true
    check_datasets: true
    min_downloads: 100
    priority_tags:
      - "text-generation"
      - "text-classification"
      - "image-classification"
      - "object-detection"
      - "image-to-text"
      - "text-to-image"
      - "automatic-speech-recognition"
      - "text-to-speech"
      - "video-classification"
      - "multimodal"

  arxiv:
    enabled: true
    categories:
      - "cs.AI"
      - "cs.LG"
      - "cs.CL"
      - "stat.ML"
    keywords:
      - "language model"
      - "transformer"
      - "benchmark"
      - "evaluation"
      - "diffusion"
      - "multimodal"

  kaggle:
    enabled: {bool(os.environ.get('KAGGLE_USERNAME'))}
    username: "{os.environ.get('KAGGLE_USERNAME', '')}"
    api_key: "{os.environ.get('KAGGLE_KEY', '')}"
    check_datasets: true
    check_models: true
    min_votes: 5

  github:
    enabled: {bool(os.environ.get('GITHUB_TOKEN'))}
    token: "{os.environ.get('GITHUB_TOKEN', '')}"
    topics:
      - "machine-learning"
      - "deep-learning"
      - "llm"
      - "transformer"
      - "diffusion"
    min_stars: 50

neo_context:
  description: |
    NEO is an autonomous AI/ML evaluation agent that tests and evaluates the latest AI/ML models
    across all modalities.

  capabilities:
    - "Full access to HuggingFace (models, datasets, spaces)"
    - "Can evaluate language models (LLMs, chat models, instruction models)"
    - "Can evaluate image models (generation, classification, detection)"
    - "Can evaluate audio/voice models (speech recognition, TTS)"
    - "Can evaluate video models (video generation, classification)"
    - "Can evaluate multimodal models (vision-language, audio-visual)"
    - "Can run comprehensive benchmarks"

  limitations:
    - "Limited to publicly available models"
    - "Must have clear evaluation criteria"
    - "Prefers models with documentation"

filtering:
  min_relevance_score: 60
  max_items_per_run: 15

  scoring:
    dimension_weights:
      relevance: 0.30
      quality: 0.20
      novelty: 0.25
      evaluability: 0.20
      impact: 0.05
    min_confidence: 0.5

  thresholds:
    default: 60
    platform_specific:
      huggingface: 65
      github: 55
      arxiv: 70
      kaggle: 60
    adaptive:
      enabled: true
      min_threshold: 50
      max_threshold: 75

  selection:
    use_diversity_constraints: true
    diversity_constraints:
      max_per_platform: 7
      max_per_modality: 8
      min_platforms: 2
      max_similar_tasks: 4
    use_priority_queue: false

  exclude_keywords:
    - "private"
    - "deprecated"
    - "archived"

  priority_keywords:
    - "sota"
    - "state-of-the-art"
    - "benchmark"
    - "latest"
    - "gpt"
    - "llama"
    - "mistral"
    - "qwen"
    - "diffusion"
    - "multimodal"

storage:
  database: "/tmp/releases.db"
  retention_days: 30
"""

    with open(config_path, 'w') as f:
        f.write(config_content)

    logger.info(f"Created config at {config_path}")
    logger.info(f"Discord webhook: {'✓ Set' if os.environ.get('DISCORD_WEBHOOK_URL') else '✗ Missing'}")
    logger.info(f"OpenRouter API key: {'✓ Set' if os.environ.get('OPENROUTER_API_KEY') else '✗ Missing'}")
    logger.info(f"S3 bucket: {'✓ ' + os.environ.get('S3_BUCKET_NAME', 'Not set') if os.environ.get('S3_BUCKET_NAME') else '✗ Not set'}")


# For local testing
if __name__ == '__main__':
    # Mock context for local testing
    class MockContext:
        request_id = 'local-test'
        memory_limit_in_mb = 1024
        def get_remaining_time_in_millis(self):
            return 900000  # 15 minutes

    result = lambda_handler({}, MockContext())
    print(json.dumps(result, indent=2))
