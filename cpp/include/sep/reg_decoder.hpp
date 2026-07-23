#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace sep {

// A named bitfield within a register.
struct Field {
    std::string name;
    uint32_t lsb = 0;    // least-significant bit position (0-based)
    uint32_t width = 1;  // number of bits
};

// A decoded field value extracted from a raw register value.
struct DecodedField {
    std::string name;
    uint64_t value = 0;
    uint32_t lsb = 0;
    uint32_t width = 1;
};

// Result of comparing an expected vs. actual decode of the same spec.
struct FieldMismatch {
    std::string name;
    uint64_t expected = 0;
    uint64_t actual = 0;
};

// Decode a raw register value into its named fields per `spec`.
// Throws std::invalid_argument if a field exceeds 64 bits.
std::vector<DecodedField> decode(uint64_t raw, const std::vector<Field>& spec);

// Decode both values and return only the fields whose decoded values differ.
std::vector<FieldMismatch> compare(uint64_t expected, uint64_t actual,
                                   const std::vector<Field>& spec);

}  // namespace sep
