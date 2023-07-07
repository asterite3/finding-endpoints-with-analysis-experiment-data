package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"sync"
)

type recordProxy struct {
	jw    *json.Encoder
	fLock sync.Mutex
}

func (rp *recordProxy) RoundTrip(r *http.Request) (*http.Response, error) {
	record := makeRequestHAR(r)
	u := r.URL.String()
	log.Printf("%s %s\n", r.Method, u)
	rp.fLock.Lock()
	err := rp.jw.Encode(record)
	if err != nil {
		rp.fLock.Unlock()
		panic(err)
	}
	rp.fLock.Unlock()
	if len(u) <= 7 {
		log.Printf("request has a strange URL %#+v (url %#+v)", r, r.URL)
	}
	return http.DefaultTransport.RoundTrip(r)
}

func newRecordProxy(outFile string) *recordProxy {
	f, err := os.OpenFile(outFile, os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0644)
	if err != nil {
		panic(err)
	}
	return &recordProxy{jw: json.NewEncoder(f)}
}
