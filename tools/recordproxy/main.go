package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"

	"gopkg.in/yaml.v3"
)

func mustParseURL(u string) *url.URL {
	result, err := url.Parse(u)
	if err != nil {
		panic(err)
	}
	return result
}

func runProxy(cfg *Config, proxyTransport http.RoundTripper, bindHost string, bindPort int) {
	proxy := &httputil.ReverseProxy{
		Director: func(r *http.Request) {
			host := r.Host

			for name := range cfg.Stands {
				if name == host {
					stand := cfg.Stands[name]
					r.URL.Host = fmt.Sprintf("%s:%d", cfg.StandsAddr, stand.Port)
					r.URL.Scheme = "http"
					return
				}
			}
			log.Printf("WARNING: unknown stand %q", host)
			r.URL.Host = unknownHostMarker
			r.Host = unknownHostMarker
		},
	}
	proxy.Transport = proxyTransport

	proxyHost := fmt.Sprintf("%s:%d", bindHost, bindPort)
	log.Printf("start proxy on %q", proxyHost)
	log.Fatal(http.ListenAndServe(proxyHost, proxy))
}

func loadConfig(configPath string, chosenStand string) *Config {
	var cfg Config

	f, err := os.Open(configPath)

	if err != nil {
		panic(err)
	}

	err = yaml.NewDecoder(f).Decode(&cfg)

	if err != nil {
		panic(err)
	}

	cfgWithHosts := &Config{
		Stands:     make(map[string]*hostConfig),
		DNSSuffix:  cfg.DNSSuffix,
		StandsAddr: cfg.StandsAddr,
	}

	if chosenStand != "" {
		if _, ok := cfg.Stands[chosenStand]; !ok {
			panic("chosen stand not found in config: " + chosenStand)
		}
		log.Printf("Will proxy only stand %q", chosenStand)
	}

	for name := range cfg.Stands {
		if chosenStand != "" && name != chosenStand {
			log.Printf("Skip %q because it is not the chosen one", name)
			continue
		}
 		c := cfg.Stands[name]
		standHostname := name
		if cfg.DNSSuffix != "" {
			standHostname += "." + cfg.DNSSuffix
		}
		cfgWithHosts.Stands[standHostname] = c
	}
	return cfgWithHosts
}

func main() {
	configPath := flag.String("c", "", "config")
	outFile := flag.String("o", "./request-log.ndjson", "output file")
	bindHostFlagValue := flag.String("b", "", "bind host")
	bindPort := flag.Int("p", 8000, "bind port")
	stand := flag.String("s", "", "proxy only this stand")

	flag.Parse()

	if *configPath == "" {
		log.Fatal("config path (-c) is mandatory")
	}

	bindHost := *bindHostFlagValue

	cfg := loadConfig(*configPath, *stand)

	if bindHost == "" {
		bindHost = cfg.StandsAddr
	}

	rp := newRecordProxy(*outFile)
	ap := newAuthProxy(cfg, rp)
	sp := &stripProxy{
		transport: ap,
		cfg:       cfg,
	}
	//bindHost := "127.0.0.1"
	runProxy(cfg, sp, bindHost, *bindPort)
}
