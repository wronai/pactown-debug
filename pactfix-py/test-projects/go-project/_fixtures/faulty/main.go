package main

import "fmt"

func identity(v interface{}) interface{} {
	return v
}

func main() {
	fmt.Println(identity("ok"))
}
