package main

type loginConfig struct {
	URL  string            `yaml:"url"`
	Form map[string]string `yaml:"form"`
}

type cookieConfig struct {
	Values map[string]string `yaml:"values"`
	Login  *loginConfig      `yaml:"login"`
}

type hostConfig struct {
	Port      int          `yaml:"port"`
	Cookies   cookieConfig `yaml:"cookies"`
	StripURLS []string     `yaml:"strip_urls"`
}

type Config struct {
	Stands     map[string]*hostConfig `yaml:"stands"`
	DNSSuffix  string                 `yaml:"dns_suffix"`
	StandsAddr string                 `yaml:"stands_addr"`
}
