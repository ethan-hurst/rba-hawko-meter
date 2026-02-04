"""
Pipeline orchestrator with tiered failure handling.

Runs all data ingestors in two phases:
1. CRITICAL sources (RBA, ABS) - fail fast if any error
2. OPTIONAL sources (CoreLogic, NAB) - graceful degradation

Exit codes:
- 0: All sources succeeded
- 1: Critical source failed (pipeline failed)
- 2: Optional source(s) failed (partial success)
"""

import sys
import json
from datetime import datetime
from typing import Dict, Any, Tuple, Callable

# Import all ingestors
from pipeline.ingest import rba_data, abs_data, corelogic_scraper, nab_scraper


# Define source tiers
CRITICAL_SOURCES = [
    ('RBA Cash Rate', rba_data),
    ('ABS Economic Data', abs_data),
]

OPTIONAL_SOURCES = [
    ('CoreLogic Housing', corelogic_scraper),
    ('NAB Capacity', nab_scraper),
]


def run_pipeline() -> Dict[str, Any]:
    """
    Execute data pipeline with tiered failure handling.

    Returns:
        Dict with run metadata, results by tier, and overall status
    """
    results = {
        'run_date': datetime.utcnow().isoformat() + 'Z',
        'critical': {},
        'optional': {},
        'status': 'pending'
    }

    print("=" * 60)
    print("RBA HAWK-O-METER DATA PIPELINE")
    print("=" * 60)
    print(f"Started: {results['run_date']}\n")

    # Phase 1: Critical sources (fail fast)
    print("PHASE 1: CRITICAL SOURCES")
    print("-" * 60)

    for name, module in CRITICAL_SOURCES:
        print(f"\n[CRITICAL] {name}")
        try:
            result = module.fetch_and_save()
            results['critical'][name] = {
                'status': 'success',
                'result': result
            }
            print(f"✓ {name} completed successfully")

        except Exception as e:
            print(f"\n✗ CRITICAL FAILURE: {name} failed")
            print(f"Error: {e}")
            results['critical'][name] = {
                'status': 'failed',
                'error': str(e)
            }
            results['status'] = 'failed'

            # Print summary and exit immediately
            print("\n" + "=" * 60)
            print("PIPELINE FAILED - CRITICAL SOURCE ERROR")
            print("=" * 60)
            print(json.dumps(results, indent=2))
            sys.exit(1)

    print("\n" + "-" * 60)
    print("✓ All critical sources succeeded")

    # Phase 2: Optional sources (graceful degradation)
    print("\n\nPHASE 2: OPTIONAL SOURCES")
    print("-" * 60)

    optional_failures = []

    for name, module in OPTIONAL_SOURCES:
        print(f"\n[OPTIONAL] {name}")
        try:
            result = module.fetch_and_save()

            # Check if result indicates failure (scrapers return status dicts)
            if isinstance(result, dict) and result.get('status') == 'failed':
                print(f"⚠ WARNING: {name} failed: {result.get('error', 'Unknown error')}")
                results['optional'][name] = result
                optional_failures.append(name)
            else:
                results['optional'][name] = {
                    'status': 'success',
                    'result': result
                }
                print(f"✓ {name} completed successfully")

        except Exception as e:
            print(f"⚠ WARNING: {name} failed: {e}")
            results['optional'][name] = {
                'status': 'failed',
                'error': str(e)
            }
            optional_failures.append(name)

    # Determine final status
    if optional_failures:
        results['status'] = 'partial'
        results['optional_failures'] = optional_failures
        print(f"\n⚠ {len(optional_failures)} optional source(s) failed: {', '.join(optional_failures)}")
    else:
        results['status'] = 'success'
        print("\n✓ All optional sources succeeded")

    # Print summary
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)

    total_sources = len(CRITICAL_SOURCES) + len(OPTIONAL_SOURCES)
    critical_success = sum(1 for r in results['critical'].values() if r.get('status') == 'success')
    optional_success = sum(1 for r in results['optional'].values() if r.get('status') == 'success')
    total_success = critical_success + optional_success
    total_failures = total_sources - total_success

    print(f"Total sources: {total_sources}")
    print(f"Succeeded: {total_success}")
    print(f"Failed: {total_failures}")
    print(f"Status: {results['status'].upper()}")
    print("=" * 60)

    return results


if __name__ == '__main__':
    results = run_pipeline()

    # Print JSON summary to stdout
    print("\nJSON SUMMARY:")
    print(json.dumps(results, indent=2))

    # Exit with appropriate code
    if results['status'] == 'success':
        sys.exit(0)
    elif results['status'] == 'partial':
        sys.exit(2)
    # Failed status already exits with code 1 in run_pipeline()
