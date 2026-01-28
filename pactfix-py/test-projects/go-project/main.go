package main

import (
	"fmt"
	"net/http"
)

func greet(name string) string {
	message := "Hello, " + name
	fmt.Println(message)
	return message
}

func handler(w http.ResponseWriter, r *http.Request) {
	result := greet("World")
	fmt.Fprintf(w, result)
}

func main() {
	http.HandleFunc("/", handler)
	fmt.Println("Server starting on :8080")
	http.ListenAndServe(":8080", nil)
}
