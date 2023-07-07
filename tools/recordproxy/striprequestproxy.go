package main

import (
	"io"
	"log"
	"net/http"
	"strings"
)

const unknownHostMarker = "error-unknownstand"

type stripProxy struct {
	cfg       *Config
	transport http.RoundTripper
}

func (sp *stripProxy) RoundTrip(r *http.Request) (*http.Response, error) {
	h := r.Host

	if h == unknownHostMarker {
		return &http.Response{
			StatusCode: 400,
			Body:       io.NopCloser(strings.NewReader("unknown stand")),
		}, nil
	}
	//log.Printf("%s", h)
	rp := r.URL.Path
	if r.URL.RawQuery != "" {
		rp += "?" + r.URL.RawQuery
	}

	if hostCFG, ok := sp.cfg.Stands[h]; ok {
		for _, p := range hostCFG.StripURLS {
			if strings.HasPrefix(rp, p) {
				log.Printf("strip URL %s", rp)
				return &http.Response{
					StatusCode: 200,
					Body:       io.NopCloser(strings.NewReader("ok")),
				}, nil
			}
		}
	}
	return sp.transport.RoundTrip(r)
}
