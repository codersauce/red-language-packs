package main

import (
	"context"
	"errors"
	"slices"
	"strings"
	"testing"
)

func TestFriendlyGreeterTrimsName(t *testing.T) {
	greeter := FriendlyGreeter{Prefix: "Hello"}

	greeting, err := greeter.Greet(context.Background(), "  Go  ")
	if err != nil {
		t.Fatalf("greeting failed: %v", err)
	}
	if greeting != "Hello, Go!" {
		t.Errorf("greeting = %q, want %q", greeting, "Hello, Go!")
	}
}

func TestFriendlyGreeterHonorsCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	_, err := (FriendlyGreeter{Prefix: "Hello"}).Greet(ctx, "Go")
	if !errors.Is(err, context.Canceled) {
		t.Errorf("error = %v, want context.Canceled", err)
	}
}

func TestMapPreservesInputOrder(t *testing.T) {
	actual := Map([]string{"go", "red"}, strings.ToUpper)
	expected := []string{"GO", "RED"}

	if !slices.Equal(actual, expected) {
		t.Errorf("mapped values = %v, want %v", actual, expected)
	}
}
