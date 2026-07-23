#include "sep/log_parser.hpp"

#include <charconv>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string_view>

namespace sep {

namespace {

// Trim ASCII whitespace from both ends of a view (zero-copy).
std::string_view trim(std::string_view sv) {
    const char* ws = " \t\r\n";
    const auto begin = sv.find_first_not_of(ws);
    if (begin == std::string_view::npos) {
        return {};
    }
    const auto end = sv.find_last_not_of(ws);
    return sv.substr(begin, end - begin + 1);
}

// Parse a double from a view. Falls back to std::stod for locales/edge cases
// not handled by from_chars on every stdlib.
double to_double(std::string_view sv) {
    double out = 0.0;
    const auto* first = sv.data();
    const auto* last = sv.data() + sv.size();
    auto [ptr, ec] = std::from_chars(first, last, out);
    if (ec == std::errc() && ptr == last) {
        return out;
    }
    return std::stod(std::string(sv));
}

// Split a line on ',' into up to `max` fields (zero-copy views).
std::vector<std::string_view> split(std::string_view line, char delim) {
    std::vector<std::string_view> fields;
    size_t start = 0;
    while (true) {
        const auto pos = line.find(delim, start);
        if (pos == std::string_view::npos) {
            fields.push_back(line.substr(start));
            break;
        }
        fields.push_back(line.substr(start, pos - start));
        start = pos + 1;
    }
    return fields;
}

std::vector<TestRecord> parse_stream(std::istream& in) {
    std::vector<TestRecord> records;
    std::string line;
    size_t lineno = 0;
    while (std::getline(in, line)) {
        ++lineno;
        std::string_view sv = trim(line);
        if (sv.empty() || sv.front() == '#') {
            continue;
        }
        const auto fields = split(sv, ',');
        if (fields.size() < 5) {
            throw std::runtime_error("malformed line " + std::to_string(lineno) +
                                     ": expected 5 fields");
        }
        TestRecord rec;
        rec.die_id = std::string(trim(fields[0]));
        rec.test_name = std::string(trim(fields[1]));
        rec.value = to_double(trim(fields[2]));
        rec.lower_limit = to_double(trim(fields[3]));
        rec.upper_limit = to_double(trim(fields[4]));
        rec.pass = (rec.value >= rec.lower_limit) && (rec.value <= rec.upper_limit);
        records.push_back(std::move(rec));
    }
    return records;
}

}  // namespace

std::vector<TestRecord> parse_log(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        throw std::runtime_error("could not open log file: " + path);
    }
    return parse_stream(in);
}

std::vector<TestRecord> parse_log_string(const std::string& contents) {
    std::istringstream in(contents);
    return parse_stream(in);
}

}  // namespace sep
