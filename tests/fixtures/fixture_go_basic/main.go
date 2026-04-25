package main

import (
	"errors"
)

// Add returns the sum of two integers.
func Add(a, b int) int {
	return a + b
}

// Divide returns a / b or an error.
func Divide(a, b int) (int, error) {
	if b == 0 {
		return 0, errors.New("division by zero")
	}
	return a / b, nil
}
