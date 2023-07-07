package main

import (
	"net/http"
	"testing"
)

func TestRemoveCookie(t *testing.T) {
	r, err := http.NewRequest("GET", "http://example.com/", nil)
	if err != nil {
		t.Fatal(err)
	}
	r.AddCookie(&http.Cookie{
		Name:  "JSESSIONID",
		Value: "k3aOXzOQinlcJ1Yk9PLJLT8u7BpA0LBywphpW6QP",
	})
	r.AddCookie(&http.Cookie{
		Name:  "85f1607f955c66a279eb54fd830a768c",
		Value: "om11uutt4bk9ddd8sojnmrcurm",
	})
	r.AddCookie(&http.Cookie{
		Name:  "security",
		Value: "medium",
	})
	removeCookie(r, "85f1607f955c66a279eb54fd830a768c")
	nCookies := len(r.Cookies())
	if nCookies != 2 {
		t.Errorf("Expected request to have 2 cookies, but have %d", nCookies)
	}
	jsessionid, err := r.Cookie("JSESSIONID")
	if err != nil {
		t.Fatal(err)
	}
	if jsessionid.Value != "k3aOXzOQinlcJ1Yk9PLJLT8u7BpA0LBywphpW6QP" {
		t.Error("bad JSESSIONID")
	}
	security, err := r.Cookie("security")
	if err != nil {
		t.Fatal(err)
	}
	if security.Value != "medium" {
		t.Error("bad security")
	}
}
