#!/usr/bin/env python3
"""Local testing script for Lambda handler."""
import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables for testing
os.environ['DISCORD_WEBHOOK_URL'] = os.getenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/test')
os.environ['OPENROUTER_API_KEY'] = os.getenv('OPENROUTER_API_KEY', 'sk-or-v1-test')
os.environ['S3_BUCKET_NAME'] = ''  # Leave empty for local testing
os.environ['DATABASE_PATH'] = '/tmp/test_releases.db'

# Mock Lambda context
class MockLambdaContext:
    """Mock Lambda context for local testing."""

    def __init__(self):
        self.function_name = 'llmeval-monitor-local'
        self.function_version = '$LATEST'
        self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:llmeval-monitor-local'
        self.memory_limit_in_mb = 2048
        self.request_id = 'local-test-' + str(os.getpid())
        self.log_group_name = '/aws/lambda/llmeval-monitor-local'
        self.log_stream_name = '2024/01/01/[$LATEST]test'
        self._remaining_time = 900000  # 15 minutes in milliseconds

    def get_remaining_time_in_millis(self):
        """Return remaining execution time in milliseconds."""
        return self._remaining_time


def test_lambda_handler():
    """Test the Lambda handler locally."""
    print("=" * 80)
    print("LlmEval Lambda Handler - Local Test")
    print("=" * 80)
    print()

    # Import handler
    from lambda_deploy.lambda_handler import lambda_handler

    # Create mock context
    context = MockLambdaContext()

    # Create test event
    event = {}

    print("📋 Test Configuration:")
    print(f"  Function Name: {context.function_name}")
    print(f"  Memory Limit: {context.memory_limit_in_mb} MB")
    print(f"  Request ID: {context.request_id}")
    print(f"  Database Path: {os.environ.get('DATABASE_PATH')}")
    print(f"  Discord Webhook: {'✓ Set' if os.environ.get('DISCORD_WEBHOOK_URL') else '✗ Not set'}")
    print(f"  OpenRouter Key: {'✓ Set' if os.environ.get('OPENROUTER_API_KEY') else '✗ Not set'}")
    print(f"  S3 Bucket: {os.environ.get('S3_BUCKET_NAME') or 'Not configured (local only)'}")
    print()

    # Check if API keys are set
    if not os.environ.get('OPENROUTER_API_KEY') or os.environ.get('OPENROUTER_API_KEY') == 'sk-or-v1-test':
        print("⚠️  WARNING: OPENROUTER_API_KEY not set or using test key!")
        print("   Set it with: export OPENROUTER_API_KEY='your-key'")
        print()
        response = input("Continue with test key (will fail on LLM calls)? (y/n): ")
        if response.lower() != 'y':
            print("Test cancelled. Please set environment variables and try again.")
            return

    print("🚀 Starting Lambda handler execution...")
    print()

    try:
        # Call handler
        result = lambda_handler(event, context)

        print()
        print("=" * 80)
        print("✅ Lambda Handler Execution Completed")
        print("=" * 80)
        print()

        # Print result
        print("📊 Result:")
        print(json.dumps(result, indent=2))
        print()

        # Check database
        db_path = os.environ.get('DATABASE_PATH', '/tmp/test_releases.db')
        if os.path.exists(db_path):
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get stats
            cursor.execute("SELECT COUNT(*) FROM releases")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM releases WHERE sent_to_discord = 1")
            sent = cursor.fetchone()[0]

            conn.close()

            print("📦 Database Stats:")
            print(f"  Total releases: {total}")
            print(f"  Sent to Discord: {sent}")
            print(f"  Database location: {db_path}")
        else:
            print("⚠️  No database created")

        print()
        print("=" * 80)
        print("Test completed successfully! ✅")
        print("=" * 80)

        return result

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ Lambda Handler Execution Failed")
        print("=" * 80)
        print()
        print(f"Error: {str(e)}")
        print()

        import traceback
        print("Full Traceback:")
        traceback.print_exc()

        print()
        print("=" * 80)
        print("Test failed! ❌")
        print("=" * 80)

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


if __name__ == '__main__':
    # Load environment from .env if exists
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        print(f"Loading environment from {env_file}")
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print()

    result = test_lambda_handler()

    # Exit with appropriate code
    sys.exit(0 if result.get('statusCode') == 200 else 1)
