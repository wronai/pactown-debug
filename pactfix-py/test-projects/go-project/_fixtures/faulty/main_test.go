package main

import (
	"os"
	"strings"
	"testing"
)

func TestPactfixRewritesInterfaceToAny(t *testing.T) {
	b, err := os.ReadFile("main.go")
	if err != nil {
		t.Fatal(err)
	}
	s := string(b)
	if strings.Contains(s, "interface{}") {
		t.Fatalf("expected pactfix to rewrite interface{} to any")
	}
	if !strings.Contains(s, " any") {
		t.Fatalf("expected rewritten code to contain 'any'")
	}
}
