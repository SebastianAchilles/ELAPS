#ifndef SAMPLER_HPP
#define SAMPLER_HPP

#include "MemoryManager.hpp"
#include "Signature.hpp"
#include "CallParser.hpp"

#include <vector>
#include <map>
#include <string>

class Sampler {
    private:
        std::map<const std::string, Signature> signatures;

        MemoryManager mem;
        std::vector<CallParser> callparsers;

        std::vector<int> counters;

        template <typename T> void named_malloc(const std::vector<std::string> &tokens);
        template <typename T> void named_offset(const std::vector<std::string> &tokens);
        void named_free(const std::vector<std::string> &tokens);
        void add_call(const std::vector<std::string> &tokens);
        void go(const std::vector<std::string> &tokens);

        void print(const std::vector<std::string> &tokens);
        void date(const std::vector<std::string> &tokens);

    public:
        void set_counters(const std::vector<std::string> &tokens);
        void add_signature(const Signature &signature);
        void start();
};

#endif /* SAMPLER_HPP */
