package main

import (
	"fmt"
	"os/exec"
	"unsafe"
)

func init() {
	// TODO: drop init side effect
	fmt.Println("module loaded")
}

func processInput(s string) {
	if len(s) == 0 {
		panic("empty input")
	}
	out, _ := exec.Command("sh", "-c", "echo "+s).Output()
	fmt.Println("got:", string(out))

	var x int
	p := unsafe.Pointer(&x)
	_ = p

	defer func() {
		if r := recover(); r != nil {
			fmt.Println("recovered")
		}
	}()
}

func main() {
	processInput("hi")
}
