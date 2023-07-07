package main

import (
	"bytes"
	"io"
	"net/http"
	"strings"
)

type KeyValue struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

type Parameters []*KeyValue

type PostData struct {
	MimeType string     `json:"mimeType"`
	Text     string     `json:"text"`
	Params   Parameters `json:"params"`
}

type RequestHAR struct {
	Method      string     `json:"method"`
	URL         string     `json:"url"`
	Headers     Parameters `json:"headers"`
	QueryString Parameters `json:"queryString"`
	PostData    *PostData  `json:"postData,omitempty"`
}

func parseQS(qs string) Parameters {
	var result Parameters

	if len(qs) == 0 {
		return result
	}

	for _, part := range strings.Split(qs, "&") {
		kv := strings.SplitN(part, "=", 2)
		k := kv[0]
		v := ""
		if len(kv) > 1 {
			v = kv[1]
		}
		result = append(result, &KeyValue{Name: k, Value: v})
	}
	return result
}

func parametersFromValues(values map[string][]string) Parameters {
	var result Parameters
	for k := range values {
		for _, v := range values[k] {
			result = append(result, &KeyValue{
				Name:  k,
				Value: v,
			})
		}
	}
	return result
}

func makeRequestHAR(r *http.Request) *RequestHAR {
	result := &RequestHAR{
		Method:      r.Method,
		URL:         r.URL.String(),
		QueryString: parseQS(r.URL.RawQuery),
	}
	result.Headers = parametersFromValues(map[string][]string(r.Header))
	if r.Body == nil {
		return result
	}
	body, err := io.ReadAll(r.Body)
	if err != nil {
		panic(err)
	}
	GetBody := func() (io.ReadCloser, error) {
		return io.NopCloser(bytes.NewReader(body)), nil
	}
	r.Body, _ = GetBody()
	r.GetBody = GetBody
	if len(body) == 0 && (r.Method == "GET" || r.Method == "HEAD") {
		return result
	}
	ct := r.Header.Get("Content-Type")
	pd := &PostData{Text: string(body)}
	if ct != "" {
		pd.MimeType = ct
	}
	if pd.MimeType == "application/x-www-form-urlencoded" {
		err = r.ParseForm()
		if err != nil {
			panic(err)
		}
		pd.Params = parametersFromValues(map[string][]string(r.PostForm))
	} else if strings.HasPrefix(pd.MimeType, "multipart/form-data") {
		err = r.ParseMultipartForm(3221225472)
		if err != nil {
			panic(err)
		}
		pd.Params = parametersFromValues(map[string][]string(r.MultipartForm.Value))
		for k := range r.MultipartForm.File {
			pd.Params = append(pd.Params, &KeyValue{
				Name:  k,
				Value: "<FILE>",
			})
		}
	}
	result.PostData = pd
	r.Body, _ = GetBody()
	return result
}
