package main

import (
	"fmt"
	"log"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"strings"
)

type authProxy struct {
	cfg       *Config
	transport http.RoundTripper
}

func newAuthProxy(cfg *Config, transport http.RoundTripper) *authProxy {
	for name := range cfg.Stands {
		stand := cfg.Stands[name]
		if stand.Cookies.Login != nil {
			log.Printf("stand %q: logging in", name)
			logIn(stand, cfg)
		}
	}

	return &authProxy{
		cfg:       cfg,
		transport: transport,
	}
}

func logIn(stand *hostConfig, cfg *Config) {
	if stand.Cookies.Values == nil {
		stand.Cookies.Values = make(map[string]string)
	}
	standURL := fmt.Sprintf("http://%s:%d", cfg.StandsAddr, stand.Port)
	loginURL, err := url.JoinPath(standURL, stand.Cookies.Login.URL)
	if err != nil {
		panic(err)
	}
	log.Printf("logging in using URL %q", loginURL)
	loginForm := make(url.Values)
	for field := range stand.Cookies.Login.Form {
		loginForm[field] = []string{stand.Cookies.Login.Form[field]}
	}
	log.Printf("sending form %v", loginForm)
	cookieJar, err := cookiejar.New(nil)
	if err != nil {
		panic(err)
	}
	httpClient := &http.Client{Jar: cookieJar}
	resp, err := httpClient.PostForm(loginURL, loginForm)
	if err != nil {
		panic(err)
	}
	resp.Body.Close()
	statusFirstDigit := resp.StatusCode / 100
	goodStatusCode := true
	if statusFirstDigit != 2 && statusFirstDigit != 3 {
		goodStatusCode = false
		log.Printf("WARNING: login resulted in status code %d", resp.StatusCode)
	}
	receivedCookies := cookieJar.Cookies(resp.Request.URL)
	if len(receivedCookies) > 0 {
		if goodStatusCode {
			log.Printf("Successfully logged in using URL %q (status %d)", loginURL, resp.StatusCode)
		}
		log.Printf("Got %d cookies:", len(receivedCookies))
		for _, c := range receivedCookies {
			stand.Cookies.Values[c.Name] = c.Value
			log.Printf("%s=%s", c.Name, c.Value)
		}
	} else {
		log.Printf("WARNING: got no cookies")
	}
}

func removeCookie(r *http.Request, name string) {
	c := r.Header.Get("Cookie")

	if c == "" {
		return
	}

	var leftParts []string

	parts := strings.Split(c, ";")

	for _, p := range parts {
		if !strings.HasPrefix(strings.TrimSpace(p), name+"=") {
			leftParts = append(leftParts, p)
		}
	}
	if len(leftParts) == 0 {
		r.Header.Del("Cookie")
	} else {
		r.Header.Set("Cookie", strings.Join(leftParts, ";"))
	}
}

func (ap *authProxy) RoundTrip(r *http.Request) (*http.Response, error) {
	h := r.Host
	//log.Printf("%s", h)
	if cfg, ok := ap.cfg.Stands[h]; ok && cfg.Cookies.Values != nil {
		//log.Printf("add cookie for %s", h)
		for name := range cfg.Cookies.Values {
			removeCookie(r, name)
			r.AddCookie(&http.Cookie{
				Name:  name,
				Value: cfg.Cookies.Values[name],
			})
		}
	}
	return ap.transport.RoundTrip(r)
}
