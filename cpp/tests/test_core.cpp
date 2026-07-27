// Native unit tests for the C++ core (no Python / pybind11).
// Build:  cmake -S cpp/tests -B build-cpp-tests && cmake --build build-cpp-tests
// Run:    ctest --test-dir build-cpp-tests --output-on-failure

#include <cstdlib>
#include <iostream>
#include <string>

#include "sep/log_parser.hpp"
#include "sep/reg_decoder.hpp"

namespace {

int failures = 0;

void expect(bool cond, const std::string& msg) {
    if (!cond) {
        std::cerr << "FAIL: " << msg << "\n";
        ++failures;
    }
}

void test_parse_log_string() {
    const std::string text =
        "# header\n"
        "D1,VDD,0.80,0.75,0.85\n"
        "D1,IDDQ,95.0,0.0,90.0\n"
        "\n"
        "D2,VDD,0.70,0.75,0.85\n";
    const auto records = sep::parse_log_string(text);
    expect(records.size() == 3, "parse_log_string count");
    expect(records[0].pass == true, "D1 VDD should pass");
    expect(records[1].pass == false, "D1 IDDQ should fail");
    expect(records[2].pass == false, "D2 VDD should fail");
    expect(records[0].test_name == "VDD", "first test name");
}

void test_decode_and_compare() {
    std::vector<sep::Field> spec = {
        {"ENABLE", 0, 1},
        {"MODE", 1, 3},
        {"REVISION", 24, 8},
    };
    // ENABLE=1, MODE=5, REVISION=0xA0
    const uint64_t raw = (1ULL << 0) | (5ULL << 1) | (0xA0ULL << 24);
    const auto fields = sep::decode(raw, spec);
    expect(fields.size() == 3, "decode field count");
    expect(fields[0].value == 1, "ENABLE");
    expect(fields[1].value == 5, "MODE");
    expect(fields[2].value == 0xA0, "REVISION");

    std::vector<sep::Field> nibble = {{"A", 0, 4}, {"B", 4, 4}};
    const auto diffs = sep::compare(0x12, 0x1F, nibble);
    expect(diffs.size() == 1, "one mismatch");
    expect(diffs[0].name == "A", "mismatch field A");
    expect(diffs[0].expected == 0x2, "expected nibble");
    expect(diffs[0].actual == 0xF, "actual nibble");
}

}  // namespace

int main() {
    test_parse_log_string();
    test_decode_and_compare();
    if (failures != 0) {
        std::cerr << failures << " assertion(s) failed\n";
        return EXIT_FAILURE;
    }
    std::cout << "All native C++ tests passed\n";
    return EXIT_SUCCESS;
}
