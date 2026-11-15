Generated adapter registries preserve configured default headers, including API
version headers, when runtime configuration supplies an empty header map. Explicit
caller headers override matching defaults while retaining the other defaults.
