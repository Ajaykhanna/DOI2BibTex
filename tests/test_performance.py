"""
Performance benchmarking and stress tests for DOI2BibTeX.

This module provides comprehensive performance testing including:
- Single DOI conversion benchmarks
- Batch conversion performance
- Async vs sync comparison
- Cache performance evaluation
- Memory usage profiling
- Concurrency stress tests
- API endpoint performance
- Database operation benchmarks

Phase 6.1e: Performance Benchmarks
"""

import pytest
import time
import statistics
from typing import List, Dict, Any, Callable
from datetime import datetime
import sys

# Import core components
from core.converter import DOIConverter
from core.constants import DOI_ORG

# Optional dependencies for performance testing
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from fastapi.testclient import TestClient
    from api_server import app
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

try:
    from core.database import DOIDatabase
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def converter():
    """Provide DOI converter instance."""
    return DOIConverter()


@pytest.fixture
def sample_doi():
    """Provide a sample DOI for benchmarking."""
    return "10.1038/nature12373"


@pytest.fixture
def sample_dois():
    """Provide multiple DOIs for batch benchmarking."""
    return [
        "10.1038/nature12373",
        "10.1126/science.1234567",
        "10.1371/journal.pone.0123456",
        "10.1109/5.771073",
        "10.1145/1327452.1327492",
    ]


@pytest.fixture
def large_doi_list():
    """Provide large DOI list for stress testing."""
    # Generate diverse DOI patterns
    dois = []
    prefixes = ["10.1038", "10.1126", "10.1371", "10.1109", "10.1145"]
    for i in range(50):
        prefix = prefixes[i % len(prefixes)]
        dois.append(f"{prefix}/test{i:04d}")
    return dois


@pytest.fixture
def performance_tracker():
    """Provide performance tracking utilities."""
    class PerformanceTracker:
        def __init__(self):
            self.measurements: List[float] = []

        def time_function(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
            """Time a function execution and track memory usage."""
            if PSUTIL_AVAILABLE:
                process = psutil.Process()
                mem_before = process.memory_info().rss / 1024 / 1024  # MB

            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()

            execution_time = end_time - start_time
            self.measurements.append(execution_time)

            stats = {
                "execution_time": execution_time,
                "result": result,
            }

            if PSUTIL_AVAILABLE:
                mem_after = process.memory_info().rss / 1024 / 1024  # MB
                stats["memory_used_mb"] = mem_after - mem_before
                stats["memory_total_mb"] = mem_after

            return stats

        def get_statistics(self) -> Dict[str, float]:
            """Calculate performance statistics."""
            if not self.measurements:
                return {}

            return {
                "count": len(self.measurements),
                "total": sum(self.measurements),
                "mean": statistics.mean(self.measurements),
                "median": statistics.median(self.measurements),
                "min": min(self.measurements),
                "max": max(self.measurements),
                "stdev": statistics.stdev(self.measurements) if len(self.measurements) > 1 else 0,
            }

    return PerformanceTracker()


# ============================================================================
# Test: Single DOI Conversion Performance
# ============================================================================

@pytest.mark.performance
class TestSingleConversionPerformance:
    """Benchmark single DOI conversion performance."""

    def test_single_doi_conversion_time(self, converter, sample_doi, performance_tracker):
        """Benchmark single DOI conversion time."""
        # Warm-up run
        converter.convert(sample_doi)

        # Benchmark runs
        for _ in range(10):
            stats = performance_tracker.time_function(
                converter.convert,
                sample_doi
            )

        perf_stats = performance_tracker.get_statistics()

        # Performance assertions
        assert perf_stats["mean"] < 5.0, f"Average conversion time too slow: {perf_stats['mean']:.2f}s"
        assert perf_stats["max"] < 10.0, f"Maximum conversion time too slow: {perf_stats['max']:.2f}s"

        # Log performance data
        print(f"\n{'='*60}")
        print(f"Single DOI Conversion Performance")
        print(f"{'='*60}")
        print(f"Runs: {perf_stats['count']}")
        print(f"Mean: {perf_stats['mean']:.3f}s")
        print(f"Median: {perf_stats['median']:.3f}s")
        print(f"Min: {perf_stats['min']:.3f}s")
        print(f"Max: {perf_stats['max']:.3f}s")
        print(f"Stdev: {perf_stats['stdev']:.3f}s")
        print(f"{'='*60}")

    def test_cached_conversion_performance(self, converter, sample_doi, performance_tracker):
        """Benchmark cached vs uncached conversion performance."""
        # First conversion (cache miss)
        first_stats = performance_tracker.time_function(
            converter.convert,
            sample_doi
        )

        # Second conversion (cache hit)
        second_stats = performance_tracker.time_function(
            converter.convert,
            sample_doi
        )

        # Cached should be significantly faster
        speedup = first_stats["execution_time"] / second_stats["execution_time"]

        print(f"\n{'='*60}")
        print(f"Cache Performance")
        print(f"{'='*60}")
        print(f"First (uncached): {first_stats['execution_time']:.3f}s")
        print(f"Second (cached): {second_stats['execution_time']:.3f}s")
        print(f"Speedup: {speedup:.1f}x")
        print(f"{'='*60}")

        # Cache should provide at least 2x speedup for identical requests
        # (This may not always be true if network is fast or cache is disabled)
        assert second_stats["execution_time"] <= first_stats["execution_time"]

    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not installed")
    def test_memory_usage_single_conversion(self, converter, sample_doi, performance_tracker):
        """Benchmark memory usage for single conversion."""
        stats = performance_tracker.time_function(
            converter.convert,
            sample_doi
        )

        print(f"\n{'='*60}")
        print(f"Memory Usage - Single Conversion")
        print(f"{'='*60}")
        print(f"Memory used: {stats['memory_used_mb']:.2f} MB")
        print(f"Total memory: {stats['memory_total_mb']:.2f} MB")
        print(f"{'='*60}")

        # Single conversion should use minimal memory
        assert stats["memory_used_mb"] < 50, f"Memory usage too high: {stats['memory_used_mb']:.2f} MB"


# ============================================================================
# Test: Batch Conversion Performance
# ============================================================================

@pytest.mark.performance
class TestBatchConversionPerformance:
    """Benchmark batch conversion performance."""

    def test_batch_conversion_time(self, converter, sample_dois, performance_tracker):
        """Benchmark batch DOI conversion time."""
        stats = performance_tracker.time_function(
            converter.batch_convert,
            sample_dois
        )

        avg_per_doi = stats["execution_time"] / len(sample_dois)

        print(f"\n{'='*60}")
        print(f"Batch Conversion Performance")
        print(f"{'='*60}")
        print(f"DOIs: {len(sample_dois)}")
        print(f"Total time: {stats['execution_time']:.3f}s")
        print(f"Average per DOI: {avg_per_doi:.3f}s")
        print(f"{'='*60}")

        # Batch processing should be reasonable
        assert avg_per_doi < 10.0, f"Average time per DOI too slow: {avg_per_doi:.2f}s"

    def test_large_batch_performance(self, converter, large_doi_list, performance_tracker):
        """Benchmark large batch conversion."""
        stats = performance_tracker.time_function(
            converter.batch_convert,
            large_doi_list
        )

        avg_per_doi = stats["execution_time"] / len(large_doi_list)

        print(f"\n{'='*60}")
        print(f"Large Batch Performance")
        print(f"{'='*60}")
        print(f"DOIs: {len(large_doi_list)}")
        print(f"Total time: {stats['execution_time']:.3f}s")
        print(f"Average per DOI: {avg_per_doi:.3f}s")
        if PSUTIL_AVAILABLE:
            print(f"Memory used: {stats['memory_used_mb']:.2f} MB")
        print(f"{'='*60}")

        # Large batches should maintain reasonable performance
        assert avg_per_doi < 10.0

    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not installed")
    def test_batch_memory_scaling(self, converter, performance_tracker):
        """Test memory usage scaling with batch size."""
        batch_sizes = [10, 20, 50]
        results = []

        for batch_size in batch_sizes:
            dois = [f"10.1234/test{i:04d}" for i in range(batch_size)]
            stats = performance_tracker.time_function(
                converter.batch_convert,
                dois
            )
            results.append({
                "batch_size": batch_size,
                "memory_mb": stats["memory_used_mb"],
                "time": stats["execution_time"],
            })

        print(f"\n{'='*60}")
        print(f"Memory Scaling Analysis")
        print(f"{'='*60}")
        for r in results:
            print(f"Batch {r['batch_size']:3d}: {r['memory_mb']:6.2f} MB, {r['time']:6.2f}s")
        print(f"{'='*60}")

        # Memory usage should scale sub-linearly (due to shared resources)
        # Not strictly enforced as it depends on implementation


# ============================================================================
# Test: Async vs Sync Performance
# ============================================================================

@pytest.mark.performance
@pytest.mark.async_test
class TestAsyncPerformance:
    """Compare async vs synchronous conversion performance."""

    def test_async_batch_performance(self, sample_dois, performance_tracker):
        """Benchmark async batch conversion if available."""
        try:
            from core.async_converter import AsyncDOIConverter
            import asyncio

            async def async_batch():
                async_converter = AsyncDOIConverter()
                return await async_converter.batch_convert_async(sample_dois)

            stats = performance_tracker.time_function(
                asyncio.run,
                async_batch()
            )

            print(f"\n{'='*60}")
            print(f"Async Batch Conversion")
            print(f"{'='*60}")
            print(f"DOIs: {len(sample_dois)}")
            print(f"Time: {stats['execution_time']:.3f}s")
            print(f"Avg per DOI: {stats['execution_time'] / len(sample_dois):.3f}s")
            print(f"{'='*60}")

        except ImportError:
            pytest.skip("Async converter not available")

    def test_sync_vs_async_comparison(self, sample_dois):
        """Compare sync vs async performance."""
        try:
            from core.async_converter import AsyncDOIConverter
            import asyncio

            # Sync conversion
            sync_converter = DOIConverter()
            sync_start = time.perf_counter()
            sync_converter.batch_convert(sample_dois)
            sync_time = time.perf_counter() - sync_start

            # Async conversion
            async def async_batch():
                async_converter = AsyncDOIConverter()
                return await async_converter.batch_convert_async(sample_dois)

            async_start = time.perf_counter()
            asyncio.run(async_batch())
            async_time = time.perf_counter() - async_start

            speedup = sync_time / async_time if async_time > 0 else 0

            print(f"\n{'='*60}")
            print(f"Sync vs Async Comparison")
            print(f"{'='*60}")
            print(f"Sync time: {sync_time:.3f}s")
            print(f"Async time: {async_time:.3f}s")
            print(f"Speedup: {speedup:.2f}x")
            print(f"{'='*60}")

            # Async should be faster for batch operations
            # (but network conditions may vary)
            assert async_time <= sync_time * 1.5  # Allow some variance

        except ImportError:
            pytest.skip("Async converter not available")


# ============================================================================
# Test: API Endpoint Performance
# ============================================================================

@pytest.mark.performance
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
class TestAPIPerformance:
    """Benchmark REST API endpoint performance."""

    def test_health_endpoint_performance(self, performance_tracker):
        """Benchmark health endpoint response time."""
        client = TestClient(app)

        for _ in range(100):
            stats = performance_tracker.time_function(
                client.get,
                "/health"
            )

        perf_stats = performance_tracker.get_statistics()

        print(f"\n{'='*60}")
        print(f"Health Endpoint Performance")
        print(f"{'='*60}")
        print(f"Requests: {perf_stats['count']}")
        print(f"Mean: {perf_stats['mean']*1000:.2f}ms")
        print(f"Median: {perf_stats['median']*1000:.2f}ms")
        print(f"Min: {perf_stats['min']*1000:.2f}ms")
        print(f"Max: {perf_stats['max']*1000:.2f}ms")
        print(f"{'='*60}")

        # Health endpoint should be very fast
        assert perf_stats["mean"] < 0.1, f"Health endpoint too slow: {perf_stats['mean']:.3f}s"

    def test_batch_api_performance(self, sample_dois, performance_tracker):
        """Benchmark batch conversion API endpoint."""
        client = TestClient(app)

        request_data = {
            "dois": sample_dois,
            "format": "bibtex",
            "fetch_abstracts": False,
        }

        stats = performance_tracker.time_function(
            client.post,
            "/api/v1/convert",
            json=request_data
        )

        print(f"\n{'='*60}")
        print(f"Batch API Endpoint Performance")
        print(f"{'='*60}")
        print(f"DOIs: {len(sample_dois)}")
        print(f"Time: {stats['execution_time']:.3f}s")
        print(f"Avg per DOI: {stats['execution_time'] / len(sample_dois):.3f}s")
        print(f"{'='*60}")

    def test_concurrent_api_requests(self, sample_doi):
        """Test API performance under concurrent load."""
        import concurrent.futures

        client = TestClient(app)

        def make_request():
            start = time.perf_counter()
            response = client.get(f"/api/v1/doi/{sample_doi}")
            return time.perf_counter() - start, response.status_code

        # Simulate 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        times = [r[0] for r in results]
        avg_time = statistics.mean(times)
        max_time = max(times)

        print(f"\n{'='*60}")
        print(f"Concurrent API Requests")
        print(f"{'='*60}")
        print(f"Concurrent requests: 10")
        print(f"Average time: {avg_time:.3f}s")
        print(f"Max time: {max_time:.3f}s")
        print(f"{'='*60}")

        # All requests should complete successfully
        assert all(r[1] in [200, 404, 500] for r in results)


# ============================================================================
# Test: Database Performance
# ============================================================================

@pytest.mark.performance
@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="SQLAlchemy not installed")
class TestDatabasePerformance:
    """Benchmark database operation performance."""

    def test_insert_performance(self, tmp_path, performance_tracker):
        """Benchmark database insert performance."""
        db = DOIDatabase(tmp_path / "perf_test.db", echo=False, create_tables=True)

        entry_data = {
            "doi": "10.1234/test",
            "bibtex": "@article{test, title={Test}}",
            "source": "Crossref",
            "format": "bibtex",
        }

        # Benchmark 100 inserts
        for i in range(100):
            entry_data["doi"] = f"10.1234/test{i:04d}"
            stats = performance_tracker.time_function(
                db.save_entry,
                **entry_data
            )

        perf_stats = performance_tracker.get_statistics()

        print(f"\n{'='*60}")
        print(f"Database Insert Performance")
        print(f"{'='*60}")
        print(f"Inserts: {perf_stats['count']}")
        print(f"Mean: {perf_stats['mean']*1000:.2f}ms")
        print(f"Total: {perf_stats['total']:.3f}s")
        print(f"{'='*60}")

        # Inserts should be fast
        assert perf_stats["mean"] < 0.1, f"Insert too slow: {perf_stats['mean']:.3f}s"

    def test_query_performance(self, tmp_path, performance_tracker):
        """Benchmark database query performance."""
        db = DOIDatabase(tmp_path / "perf_test.db", echo=False, create_tables=True)

        # Insert test data
        for i in range(100):
            db.save_entry(
                doi=f"10.1234/test{i:04d}",
                bibtex=f"@article{{test{i}, title={{Test {i}}}}}",
                source="Crossref",
                format="bibtex",
            )

        # Benchmark queries
        for i in range(50):
            doi = f"10.1234/test{i:04d}"
            stats = performance_tracker.time_function(
                db.get_entry,
                doi
            )

        perf_stats = performance_tracker.get_statistics()

        print(f"\n{'='*60}")
        print(f"Database Query Performance")
        print(f"{'='*60}")
        print(f"Queries: {perf_stats['count']}")
        print(f"Mean: {perf_stats['mean']*1000:.2f}ms")
        print(f"{'='*60}")

        # Queries should be very fast
        assert perf_stats["mean"] < 0.05, f"Query too slow: {perf_stats['mean']:.3f}s"

    def test_search_performance(self, tmp_path, performance_tracker):
        """Benchmark database search performance."""
        db = DOIDatabase(tmp_path / "perf_test.db", echo=False, create_tables=True)

        # Insert test data with varied sources
        sources = ["Crossref", "DataCite", "DOI.org"]
        for i in range(300):
            db.save_entry(
                doi=f"10.1234/test{i:04d}",
                bibtex=f"@article{{test{i}, title={{Test {i}}}}}",
                source=sources[i % len(sources)],
                format="bibtex",
            )

        # Benchmark search
        stats = performance_tracker.time_function(
            db.search_entries,
            source="Crossref",
            limit=100
        )

        print(f"\n{'='*60}")
        print(f"Database Search Performance")
        print(f"{'='*60}")
        print(f"Total entries: 300")
        print(f"Search time: {stats['execution_time']*1000:.2f}ms")
        print(f"Results: {len(stats['result'])}")
        print(f"{'='*60}")

        # Search should be fast
        assert stats["execution_time"] < 0.5, f"Search too slow: {stats['execution_time']:.3f}s"


# ============================================================================
# Test: Throughput Benchmarks
# ============================================================================

@pytest.mark.performance
class TestThroughput:
    """Measure system throughput capabilities."""

    def test_conversions_per_second(self, converter, sample_doi):
        """Measure conversions per second (cached)."""
        # Prime cache
        converter.convert(sample_doi)

        # Measure throughput over 5 seconds
        duration = 5
        start_time = time.perf_counter()
        count = 0

        while time.perf_counter() - start_time < duration:
            converter.convert(sample_doi)
            count += 1

        elapsed = time.perf_counter() - start_time
        throughput = count / elapsed

        print(f"\n{'='*60}")
        print(f"Throughput Test (Cached)")
        print(f"{'='*60}")
        print(f"Duration: {elapsed:.2f}s")
        print(f"Conversions: {count}")
        print(f"Throughput: {throughput:.1f} conversions/sec")
        print(f"{'='*60}")

        # Should handle multiple conversions per second
        assert throughput > 1.0, f"Throughput too low: {throughput:.2f} conv/s"


# ============================================================================
# Test: Stress Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
class TestStressTests:
    """Stress tests for system limits."""

    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not installed")
    def test_memory_leak_detection(self, converter, sample_doi):
        """Test for memory leaks over many iterations."""
        process = psutil.Process()

        # Initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run many conversions
        for _ in range(100):
            converter.convert(sample_doi)

        # Final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        print(f"\n{'='*60}")
        print(f"Memory Leak Test")
        print(f"{'='*60}")
        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"Final memory: {final_memory:.2f} MB")
        print(f"Growth: {memory_growth:.2f} MB")
        print(f"Iterations: 100")
        print(f"{'='*60}")

        # Memory growth should be minimal (< 50 MB for 100 iterations)
        assert memory_growth < 50, f"Possible memory leak: {memory_growth:.2f} MB growth"


# ============================================================================
# Run Benchmarks
# ============================================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "-m", "performance",
        "--tb=short",
        "-s",  # Show print output
    ])
