#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "sep/log_parser.hpp"
#include "sep/reg_decoder.hpp"

namespace py = pybind11;

PYBIND11_MODULE(sep_core, m) {
    m.doc() = "Silicon Engineering Platform C++ core: log parsing + register decode";

    py::class_<sep::TestRecord>(m, "TestRecord")
        .def_readonly("die_id", &sep::TestRecord::die_id)
        .def_readonly("test_name", &sep::TestRecord::test_name)
        .def_readonly("value", &sep::TestRecord::value)
        .def_readonly("lower_limit", &sep::TestRecord::lower_limit)
        .def_readonly("upper_limit", &sep::TestRecord::upper_limit)
        .def_readonly("pass_", &sep::TestRecord::pass)
        .def("__repr__", [](const sep::TestRecord& r) {
            return "<TestRecord " + r.die_id + " " + r.test_name +
                   (r.pass ? " PASS>" : " FAIL>");
        });

    py::class_<sep::Field>(m, "Field")
        .def(py::init<>())
        .def(py::init([](std::string name, uint32_t lsb, uint32_t width) {
                 return sep::Field{std::move(name), lsb, width};
             }),
             py::arg("name"), py::arg("lsb"), py::arg("width"))
        .def_readwrite("name", &sep::Field::name)
        .def_readwrite("lsb", &sep::Field::lsb)
        .def_readwrite("width", &sep::Field::width);

    py::class_<sep::DecodedField>(m, "DecodedField")
        .def_readonly("name", &sep::DecodedField::name)
        .def_readonly("value", &sep::DecodedField::value)
        .def_readonly("lsb", &sep::DecodedField::lsb)
        .def_readonly("width", &sep::DecodedField::width)
        .def("__repr__", [](const sep::DecodedField& d) {
            return "<DecodedField " + d.name + "=" + std::to_string(d.value) + ">";
        });

    py::class_<sep::FieldMismatch>(m, "FieldMismatch")
        .def_readonly("name", &sep::FieldMismatch::name)
        .def_readonly("expected", &sep::FieldMismatch::expected)
        .def_readonly("actual", &sep::FieldMismatch::actual)
        .def("__repr__", [](const sep::FieldMismatch& d) {
            return "<FieldMismatch " + d.name + " exp=" + std::to_string(d.expected) +
                   " act=" + std::to_string(d.actual) + ">";
        });

    m.def("parse_log", &sep::parse_log, py::arg("path"),
          "Parse a test-log file into a list of TestRecord.");
    m.def("parse_log_string", &sep::parse_log_string, py::arg("contents"),
          "Parse test-log text into a list of TestRecord.");
    m.def("decode", &sep::decode, py::arg("raw"), py::arg("spec"),
          "Decode a raw register value into named fields.");
    m.def("compare", &sep::compare, py::arg("expected"), py::arg("actual"),
          py::arg("spec"), "Return fields that differ between expected and actual.");
}
