// Reference (intended) solution — used ONLY to calibrate the time limit.
// NOT served to any agent and never shown to the learner.
//
// O(n) hash-map counting: for each value x, add the number of previously-seen
// (K - x) values. Comfortably under the 1500 ms limit at n = 1e6, while the
// naive O(n^2) approach blows past it.
//
//   docker build -t cp-tutor-sandbox ./sandbox   # then run this via the pipeline,
//   or compile locally:  g++ -O2 -std=c++17 reference_solution.cpp && ./a.out < big.in
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n, k;
    if (!(cin >> n >> k)) return 0;

    unordered_map<long long, long long> seen;
    seen.reserve(n * 2);
    long long count = 0;
    for (long long i = 0; i < n; ++i) {
        long long x;
        cin >> x;
        auto it = seen.find(k - x);
        if (it != seen.end()) count += it->second;
        seen[x]++;
    }
    cout << count << "\n";
    return 0;
}
