# Agent Quick Start Guide

A practical guide to implementing AI agents for ScreenerIII development.

---

## 🚀 Quick Implementation Roadmap

### Week 1-2: Foundation
1. **Test Generation Agent** - Auto-generate unit tests
2. **Code Review Agent** - Automated PR reviews
3. **Security Scanning Agent** - Vulnerability detection

### Week 3-4: Core Functionality
4. **Market Data Collection Agent** - Continuous data ingestion
5. **Data Quality Agent** - Validation and anomaly detection
6. **Signal Generation Agent** - Real-time trading signals

### Month 2-3: Enhancement
7. **Backtesting Agent** - Strategy validation
8. **Monitoring Agent** - System observability
9. **Notification Agent** - User alerts

---

## 🎯 Phase 1 Priority Agents

### 1. Test Generation Agent (Highest ROI)

**Why First?**: Immediate productivity boost, reduces testing burden

**Setup Time**: 4-8 hours

**Implementation**:

```python
# agents/test_generator.py
from anthropic import Anthropic
import ast
import os

class TestGeneratorAgent:
    """Automatically generates pytest tests for Python modules."""

    def __init__(self):
        self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    def analyze_function(self, source_code: str) -> dict:
        """Extract function signature and docstring."""
        tree = ast.parse(source_code)
        functions = [node for node in ast.walk(tree)
                     if isinstance(node, ast.FunctionDef)]

        return {
            'name': functions[0].name if functions else None,
            'args': [arg.arg for arg in functions[0].args.args] if functions else [],
            'docstring': ast.get_docstring(functions[0]) if functions else None
        }

    def generate_tests(self, module_path: str, function_name: str = None) -> str:
        """Generate comprehensive tests for a module or function."""

        with open(module_path, 'r') as f:
            source_code = f.read()

        prompt = f"""Generate comprehensive pytest unit tests for this Python code:

```python
{source_code}
```

Requirements:
1. Test happy path scenarios
2. Test edge cases (empty inputs, None, zero, negative)
3. Test error conditions (invalid inputs, exceptions)
4. Use pytest fixtures where appropriate
5. Include docstrings explaining what each test validates
6. Mock external dependencies (API calls, database)
7. Aim for 90%+ code coverage

Generate only the test code, properly formatted with imports.
"""

        response = self.client.messages.create(
            model="claude-sonnet-4",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def save_tests(self, test_code: str, output_path: str):
        """Save generated tests to file."""
        with open(output_path, 'w') as f:
            f.write(test_code)
        print(f"Tests saved to {output_path}")


# Usage
if __name__ == "__main__":
    agent = TestGeneratorAgent()

    # Generate tests for a module
    tests = agent.generate_tests('src/analysis/indicators.py')
    agent.save_tests(tests, 'tests/unit/test_indicators_generated.py')
```

**GitHub Actions Integration**:

```yaml
# .github/workflows/test-generation.yml
name: Auto-Generate Tests

on:
  pull_request:
    paths:
      - 'src/**/*.py'

jobs:
  generate-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install anthropic pytest

      - name: Generate tests for changed files
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python agents/test_generator.py

      - name: Run generated tests
        run: pytest tests/

      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: htmlcov/
```

**Expected Results**:
- Tests generated in <1 minute per module
- 70-90% initial code coverage
- Human review for edge cases

---

### 2. Code Review Agent

**Why?**: Catch issues before human review, improve code quality

**Setup Time**: 2-4 hours

**Implementation**:

```python
# agents/code_reviewer.py
from anthropic import Anthropic
import subprocess
import os

class CodeReviewAgent:
    """Automated code review using Claude."""

    def __init__(self):
        self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    def get_diff(self, branch: str = "main") -> str:
        """Get git diff for review."""
        result = subprocess.run(
            ['git', 'diff', branch, '--', '*.py'],
            capture_output=True,
            text=True
        )
        return result.stdout

    def review_code(self, diff: str) -> dict:
        """Review code changes and provide feedback."""

        prompt = f"""Review this code diff and provide feedback:

```diff
{diff}
```

Analyze for:
1. **Bugs**: Logic errors, potential crashes, edge cases
2. **Security**: SQL injection, XSS, credential exposure, input validation
3. **Performance**: Inefficient algorithms, memory leaks, N+1 queries
4. **Style**: PEP 8 violations, naming conventions, code clarity
5. **Best Practices**: Error handling, logging, type hints, docstrings
6. **Testing**: Missing tests, test coverage concerns

Provide:
- 🔴 Critical issues (must fix)
- 🟡 Warnings (should fix)
- 🟢 Suggestions (nice to have)
- ✅ Positive feedback

Format as markdown.
"""

        response = self.client.messages.create(
            model="claude-sonnet-4",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            'review': response.content[0].text,
            'tokens': response.usage.input_tokens + response.usage.output_tokens
        }

    def post_comment(self, pr_number: int, review: str):
        """Post review as PR comment (using GitHub API)."""
        # Implement GitHub API integration
        pass


# Usage
if __name__ == "__main__":
    agent = CodeReviewAgent()
    diff = agent.get_diff("main")

    if diff:
        review = agent.review_code(diff)
        print(review['review'])
```

**GitHub Actions Integration**:

```yaml
# .github/workflows/code-review.yml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Run AI Code Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python agents/code_reviewer.py --pr ${{ github.event.pull_request.number }}
```

---

### 3. Security Scanning Agent

**Why?**: Prevent vulnerabilities from reaching production

**Setup Time**: 2-3 hours

**Implementation**:

```python
# agents/security_scanner.py
import subprocess
import json
from typing import List, Dict

class SecurityScannerAgent:
    """Automated security scanning."""

    def scan_dependencies(self) -> List[Dict]:
        """Scan dependencies for known vulnerabilities."""
        result = subprocess.run(
            ['pip-audit', '--format', 'json'],
            capture_output=True,
            text=True
        )

        if result.stdout:
            return json.loads(result.stdout)
        return []

    def scan_code(self) -> List[Dict]:
        """Scan code for security issues using bandit."""
        result = subprocess.run(
            ['bandit', '-r', 'src/', '-f', 'json'],
            capture_output=True,
            text=True
        )

        if result.stdout:
            data = json.loads(result.stdout)
            return data.get('results', [])
        return []

    def scan_secrets(self) -> List[Dict]:
        """Scan for exposed secrets using detect-secrets."""
        result = subprocess.run(
            ['detect-secrets', 'scan', '--all-files'],
            capture_output=True,
            text=True
        )

        if result.stdout:
            return json.loads(result.stdout).get('results', {})
        return {}

    def generate_report(self) -> dict:
        """Generate comprehensive security report."""
        return {
            'dependencies': self.scan_dependencies(),
            'code_issues': self.scan_code(),
            'secrets': self.scan_secrets(),
            'timestamp': datetime.now().isoformat()
        }

    def check_severity(self, report: dict) -> bool:
        """Check if there are critical issues."""
        critical_count = sum(
            1 for issue in report['code_issues']
            if issue['issue_severity'] == 'HIGH'
        )
        return critical_count == 0


# Usage
if __name__ == "__main__":
    agent = SecurityScannerAgent()
    report = agent.generate_report()

    # Fail CI if critical issues found
    if not agent.check_severity(report):
        print("❌ Critical security issues found!")
        exit(1)
    else:
        print("✅ No critical security issues")
```

**Pre-commit Hook**:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: security-scan
        name: Security Scan
        entry: python agents/security_scanner.py
        language: python
        pass_filenames: false
```

---

### 4. Market Data Collection Agent

**Why?**: Core functionality for the trading system

**Setup Time**: 8-12 hours

**Implementation**:

```python
# agents/data_collector.py
from celery import Celery
from src.data.oanda_client import OANDAClient
from src.data.storage import StorageManager
from src.core.logger import get_logger
import time

app = Celery('data_collector', broker='redis://localhost:6379/0')
logger = get_logger(__name__)

class DataCollectorAgent:
    """Continuously collect market data from OANDA."""

    def __init__(self):
        self.client = OANDAClient()
        self.storage = StorageManager()
        self.instruments = self.get_instruments()

    def get_instruments(self) -> list:
        """Get list of instruments to track."""
        from config.markets import MARKETS
        return list(MARKETS.keys())

    @app.task
    def collect_prices(self):
        """Collect current prices for all instruments."""
        try:
            prices = self.client.get_current_prices(self.instruments)
            self.storage.save_prices(prices)
            logger.info(f"Collected prices for {len(prices)} instruments")
            return True
        except Exception as e:
            logger.error(f"Price collection failed: {e}")
            return False

    @app.task
    def collect_candles(self, instrument: str, timeframe: str = 'M1'):
        """Collect historical candles."""
        try:
            candles = self.client.get_candles(
                instrument,
                count=100,
                granularity=timeframe
            )
            self.storage.save_candles(candles)
            logger.info(f"Collected {len(candles)} candles for {instrument}")
            return True
        except Exception as e:
            logger.error(f"Candle collection failed: {e}")
            return False

    def monitor_health(self):
        """Monitor data collection health."""
        last_update = self.storage.get_last_update_time()
        if (time.time() - last_update) > 60:  # 1 minute threshold
            logger.warning("Data collection delayed!")
            # Trigger alert

    def run_forever(self, interval: int = 10):
        """Run data collection loop."""
        while True:
            self.collect_prices()
            self.monitor_health()
            time.sleep(interval)


# Celery beat schedule for periodic tasks
from celery.schedules import crontab

app.conf.beat_schedule = {
    'collect-prices-every-10-seconds': {
        'task': 'agents.data_collector.collect_prices',
        'schedule': 10.0,  # Every 10 seconds
    },
    'collect-candles-every-minute': {
        'task': 'agents.data_collector.collect_candles',
        'schedule': 60.0,  # Every minute
        'args': ('EUR_USD', 'M1')
    },
}
```

**Docker Compose Integration**:

```yaml
# docker-compose.yml (add these services)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery-worker:
    build: .
    command: celery -A agents.data_collector worker --loglevel=info
    depends_on:
      - redis
      - timescaledb
    env_file:
      - .env

  celery-beat:
    build: .
    command: celery -A agents.data_collector beat --loglevel=info
    depends_on:
      - redis
    env_file:
      - .env
```

---

## 🛠️ Agent Development Toolkit

### Required Tools

```bash
# Install agent development dependencies
pip install anthropic celery redis prometheus-client

# For code analysis
pip install ast-grep bandit detect-secrets pip-audit

# For testing
pip install pytest pytest-mock pytest-asyncio

# For monitoring
pip install prometheus-client grafana-client
```

### Project Structure

```
ScreenerIII/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py          # Base class for all agents
│   ├── test_generator.py      # Test generation
│   ├── code_reviewer.py       # Code review
│   ├── security_scanner.py    # Security scanning
│   ├── data_collector.py      # Data collection
│   ├── signal_generator.py    # Signal generation
│   └── utils/
│       ├── prompts.py         # LLM prompts
│       └── monitoring.py      # Agent monitoring
├── config/
│   └── agents.yaml            # Agent configuration
└── tests/
    └── agents/                # Agent tests
```

### Base Agent Class

```python
# agents/base_agent.py
from abc import ABC, abstractmethod
from prometheus_client import Counter, Histogram
import logging
import time

class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")

        # Metrics
        self.executions = Counter(
            f'agent_{name}_executions_total',
            'Total agent executions'
        )
        self.errors = Counter(
            f'agent_{name}_errors_total',
            'Total agent errors'
        )
        self.duration = Histogram(
            f'agent_{name}_duration_seconds',
            'Agent execution duration'
        )

    @abstractmethod
    def execute(self, *args, **kwargs):
        """Execute agent task."""
        pass

    def run(self, *args, **kwargs):
        """Run agent with monitoring."""
        self.executions.inc()
        start_time = time.time()

        try:
            result = self.execute(*args, **kwargs)
            duration = time.time() - start_time
            self.duration.observe(duration)
            self.logger.info(f"Executed in {duration:.2f}s")
            return result
        except Exception as e:
            self.errors.inc()
            self.logger.error(f"Execution failed: {e}")
            raise
```

---

## 📊 Monitoring Dashboard

### Grafana Dashboard for Agents

```json
{
  "dashboard": {
    "title": "Agent Monitoring",
    "panels": [
      {
        "title": "Agent Execution Rate",
        "targets": [{
          "expr": "rate(agent_*_executions_total[5m])"
        }]
      },
      {
        "title": "Agent Error Rate",
        "targets": [{
          "expr": "rate(agent_*_errors_total[5m])"
        }]
      },
      {
        "title": "Agent Duration",
        "targets": [{
          "expr": "agent_*_duration_seconds"
        }]
      }
    ]
  }
}
```

---

## 🎯 Success Metrics

### Agent Performance KPIs

| Agent | Metric | Target | Current |
|-------|--------|--------|---------|
| Test Generator | Tests created/hr | 100+ | - |
| Code Reviewer | Reviews/day | 20+ | - |
| Data Collector | Uptime % | 99.9% | - |
| Signal Generator | Latency | <100ms | - |
| Security Scanner | Vulns found | N/A | - |

### Development Velocity Impact

**Before Agents**:
- Manual test writing: 2-4 hours/module
- Code review: 30-60 min/PR
- Security scan: Manual, infrequent
- Data collection: Manual scripts

**After Agents**:
- Test generation: 5 min/module (96% faster)
- Code review: 5 min/PR (90% faster)
- Security scan: Every commit (100% coverage)
- Data collection: 100% automated, 99.9% uptime

---

## 🚦 Next Steps

### Week 1: Foundation
1. Set up agent directory structure
2. Implement Base Agent class
3. Deploy Test Generation Agent
4. Configure GitHub Actions

### Week 2: Core Agents
5. Deploy Code Review Agent
6. Deploy Security Scanner
7. Set up monitoring dashboard

### Week 3-4: Trading Agents
8. Deploy Data Collection Agent
9. Deploy Signal Generation Agent
10. Integrate with main application

### Month 2+
11. Deploy Backtesting Agent
12. Deploy Optimization Agent
13. Add ML agents

---

## 📚 Resources

- [Agent Architecture (Full Doc)](agent-architecture.md)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Prometheus Monitoring](https://prometheus.io/docs/)

---

**Ready to implement?** Start with the Test Generation Agent - highest ROI and quickest to deploy!
