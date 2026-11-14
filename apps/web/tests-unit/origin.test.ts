import assert from "node:assert/strict";
import test from "node:test";
import { isSameOrigin } from "../lib/origin.ts";

test("Docker bind address does not override the browser-facing Host", () => {
  assert.equal(isSameOrigin("http://localhost:3000", "localhost:3000", "http:"), true);
});

test("cross-origin hosts, ports and protocols remain rejected", () => {
  for (const origin of ["http://attacker.invalid:3000", "http://localhost:4000",
                        "https://localhost:3000", "http://localhost.attacker.invalid:3000"]) {
    assert.equal(isSameOrigin(origin, "localhost:3000", "http:"), false);
  }
});

test("malformed or opaque origins are rejected", () => {
  for (const origin of ["null", "", "not-a-url", "http://localhost:3000/path",
                        "http://evil@localhost:3000", "http://localhost:3000#fragment"]) {
    assert.equal(isSameOrigin(origin, "localhost:3000", "http:"), false);
  }
});

test("missing or malformed authorities cannot authorize browser writes", () => {
  for (const host of [null, "", "evil@localhost:3000", "localhost:3000/path"]) {
    assert.equal(isSameOrigin("http://localhost:3000", host, "http:"), false);
  }
});

test("default ports and host casing use canonical URL comparison", () => {
  assert.equal(isSameOrigin("http://localhost", "LOCALHOST:80", "http:"), true);
  assert.equal(isSameOrigin("https://example.invalid", "example.invalid:443", "https:"), true);
});

test("Origin-free command-line requests preserve existing authentication behavior", () => {
  assert.equal(isSameOrigin(null, "localhost:3000", "http:"), true);
});
