#!/usr/bin/env python3
"""
Multi-Agent Validation Runner

Executes all agent test suites and generates comprehensive validation report.

Usage:
    python scripts/run_agent_validation.py

Output:
    - Console output with test results
    - AGENT_VALIDATION_REPORT.md with detailed findings
"""
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime


def run_pytest_agent_tests(test_path):
    """Run pytest for a specific agent test file and return results."""
    result = subprocess.run(
        ["pytest", str(test_path), "-v", "--tb=short", "--json-report", "--json-report-file=temp_report.json"],
        capture_output=True,
        text=True
    )

    # Try to load JSON report if available
    try:
        with open("temp_report.json") as f:
            report_data = json.load(f)
    except:
        report_data = None

    return {
        'returncode': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
        'report': report_data
    }


def generate_report(results):
    """Generate markdown report from test results."""
    report_lines = []
    report_lines.append("# Multi-Agent Frontend Validation Report\n")
    report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append("---\n\n")

    # Executive Summary
    total_tests = sum(r['total'] for r in results.values())
    total_passed = sum(r['passed'] for r in results.values())
    total_failed = sum(r['failed'] for r in results.values())

    report_lines.append("## Executive Summary\n\n")
    report_lines.append(f"- **Total Tests:** {total_tests}\n")
    report_lines.append(f"- **Passed:** {total_passed} ✅\n")
    report_lines.append(f"- **Failed:** {total_failed} ❌\n")
    report_lines.append(f"- **Success Rate:** {(total_passed/total_tests*100) if total_tests > 0 else 0:.1f}%\n\n")

    if total_failed == 0:
        report_lines.append("🎉 **All tests passed!** The system meets rate limit compliance and data accuracy standards.\n\n")
    else:
        report_lines.append("⚠️ **Action required:** Some tests failed. Review findings below.\n\n")

    # Agent Results
    report_lines.append("## Agent Test Results\n\n")

    for agent_name, agent_results in results.items():
        status = "✅ PASS" if agent_results['failed'] == 0 else "❌ FAIL"
        report_lines.append(f"### {agent_name} {status}\n\n")
        report_lines.append(f"- Tests Run: {agent_results['total']}\n")
        report_lines.append(f"- Passed: {agent_results['passed']}\n")
        report_lines.append(f"- Failed: {agent_results['failed']}\n\n")

        if agent_results['failed'] > 0 and agent_results.get('failures'):
            report_lines.append("**Failed Tests:**\n")
            for failure in agent_results['failures']:
                report_lines.append(f"- `{failure['test']}`: {failure['reason']}\n")
            report_lines.append("\n")

    # Rate Limit Compliance Summary
    report_lines.append("## Rate Limit Compliance Analysis\n\n")

    if 'Rate Limit Compliance Agent' in results:
        rl_results = results['Rate Limit Compliance Agent']
        if rl_results['failed'] == 0:
            report_lines.append("✅ **System properly protects against rate limit abuse:**\n")
            report_lines.append("- Cache effectiveness validated (hit rate > 95%)\n")
            report_lines.append("- Signals endpoint reads from database only\n")
            report_lines.append("- No external API calls triggered by frontend requests\n")
            report_lines.append("- Fallback cache activates when all APIs fail\n\n")
        else:
            report_lines.append("⚠️ **Rate limit protection needs attention** - see failed tests above.\n\n")

    # Recommendations
    report_lines.append("## Recommendations\n\n")

    if total_failed > 0:
        report_lines.append("### Immediate Actions\n\n")
        report_lines.append("1. Review and fix failed tests listed above\n")
        report_lines.append("2. Re-run validation suite after fixes\n")
        report_lines.append("3. Monitor API call rates in production\n\n")

    report_lines.append("### Ongoing Monitoring\n\n")
    report_lines.append("1. **Track cache hit rates** - Should remain > 95%\n")
    report_lines.append("2. **Monitor external API calls** - Set up alerts for unexpected spikes\n")
    report_lines.append("3. **Validate signal freshness** - Ensure bot runs regularly during market hours\n")
    report_lines.append("4. **Re-run agent tests** - Weekly validation recommended\n\n")

    return "\n".join(report_lines)


def main():
    """Main validation runner."""
    print("=" * 70)
    print("MULTI-AGENT FRONTEND VALIDATION SUITE")
    print("=" * 70)
    print()

    test_dir = Path("backend/tests/agents")
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return 1

    # Define agents to test
    agents = {
        "Rate Limit Compliance Agent": "test_agent_rate_limit_compliance.py",
        "Signal Storage Agent": "test_agent_signal_storage.py",
    }

    results = {}

    # Run each agent's tests
    for agent_name, test_file in agents.items():
        test_path = test_dir / test_file
        if not test_path.exists():
            print(f"⚠️  Skipping {agent_name} - test file not found: {test_file}")
            continue

        print(f"\n{'='*70}")
        print(f"Running: {agent_name}")
        print(f"{'='*70}\n")

        test_result = run_pytest_agent_tests(test_path)

        # Parse output for results
        passed = test_result['stdout'].count(" PASSED")
        failed = test_result['stdout'].count(" FAILED")
        total = passed + failed

        results[agent_name] = {
            'total': total,
            'passed': passed,
            'failed': failed,
            'returncode': test_result['returncode'],
            'failures': []  # Could parse from output if needed
        }

        # Print results
        print(test_result['stdout'])
        if test_result['stderr']:
            print("STDERR:", test_result['stderr'])

        status = "✅ PASSED" if failed == 0 else f"❌ FAILED ({failed}/{total})"
        print(f"\n{agent_name}: {status}\n")

    # Generate report
    print("\n" + "=" * 70)
    print("GENERATING VALIDATION REPORT")
    print("=" * 70 + "\n")

    report = generate_report(results)
    report_path = Path("AGENT_VALIDATION_REPORT.md")

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"✅ Report generated: {report_path}")
    print()
    print("=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)
    print()

    # Print summary
    total_tests = sum(r['total'] for r in results.values())
    total_passed = sum(r['passed'] for r in results.values())
    total_failed = sum(r['failed'] for r in results.values())

    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed} ✅")
    print(f"Failed: {total_failed} ❌")
    print(f"Success Rate: {(total_passed/total_tests*100) if total_tests > 0 else 0:.1f}%")
    print()

    # Return appropriate exit code
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
