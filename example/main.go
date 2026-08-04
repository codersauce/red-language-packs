package main

import (
	"context"
	"fmt"
	"strings"
)

// Greeter produces a greeting while respecting cancellation.
type Greeter interface {
	Greet(context.Context, string) (string, error)
}

// FriendlyGreeter demonstrates methods, interfaces, and struct fields.
type FriendlyGreeter struct {
	Prefix string
}

func (greeter FriendlyGreeter) Greet(ctx context.Context, name string) (string, error) {
	select {
	case <-ctx.Done():
		return "", ctx.Err()
	default:
		return fmt.Sprintf("%s, %s!", greeter.Prefix, strings.TrimSpace(name)), nil
	}
}

// Map applies a generic transformation to every input.
func Map[Input, Output any](values []Input, transform func(Input) Output) []Output {
	result := make([]Output, 0, len(values))
	for _, value := range values {
		result = append(result, transform(value))
	}
	return result
}

func main() {
	greeter := FriendlyGreeter{Prefix: "Hello from Red"}
	greeting, err := greeter.Greet(context.Background(), "Go")
	if err != nil {
		panic(err)
	}

	fmt.Println(greeting)
	fmt.Println(strings.Join(Map([]string{"syntax", "hover", "diagnostics"}, strings.ToUpper), ", "))
}
