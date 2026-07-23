#include "sep/reg_decoder.hpp"

#include <stdexcept>

namespace sep {

namespace {

// Extract `width` bits starting at `lsb` from `raw`.
uint64_t extract(uint64_t raw, uint32_t lsb, uint32_t width) {
    if (width == 0 || width > 64) {
        throw std::invalid_argument("field width must be in 1..64");
    }
    if (lsb + width > 64) {
        throw std::invalid_argument("field exceeds 64-bit register bounds");
    }
    // Mask of `width` ones; guard the width==64 shift which is UB.
    const uint64_t mask = (width == 64) ? ~uint64_t(0) : ((uint64_t(1) << width) - 1);
    return (raw >> lsb) & mask;
}

}  // namespace

std::vector<DecodedField> decode(uint64_t raw, const std::vector<Field>& spec) {
    std::vector<DecodedField> out;
    out.reserve(spec.size());
    for (const auto& f : spec) {
        DecodedField df;
        df.name = f.name;
        df.lsb = f.lsb;
        df.width = f.width;
        df.value = extract(raw, f.lsb, f.width);
        out.push_back(std::move(df));
    }
    return out;
}

std::vector<FieldMismatch> compare(uint64_t expected, uint64_t actual,
                                   const std::vector<Field>& spec) {
    std::vector<FieldMismatch> diffs;
    for (const auto& f : spec) {
        const uint64_t e = extract(expected, f.lsb, f.width);
        const uint64_t a = extract(actual, f.lsb, f.width);
        if (e != a) {
            diffs.push_back(FieldMismatch{f.name, e, a});
        }
    }
    return diffs;
}

}  // namespace sep
