#pragma once

#include <string>
#include <vector>

namespace sep {

// One parsed line from a post-silicon test log.
struct TestRecord {
    std::string die_id;
    std::string test_name;
    double value = 0.0;
    double lower_limit = 0.0;
    double upper_limit = 0.0;
    bool pass = false;
};

// Parse a test-log file into structured records.
//
// Expected line format (comments starting with '#' and blank lines ignored):
//   die_id,test_name,value,lower_limit,upper_limit
// `pass` is computed as (lower_limit <= value <= upper_limit).
//
// Throws std::runtime_error if the file cannot be opened.
std::vector<TestRecord> parse_log(const std::string& path);

// Parse from an in-memory string (same format). Useful for tests.
std::vector<TestRecord> parse_log_string(const std::string& contents);

}  // namespace sep
