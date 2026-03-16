.PHONY: certs certs-reload certs-check

certs:
	mkcert -install
	mkdir -p .certs
	mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem localhost 127.0.0.1 ::1

certs-reload: certs
	docker compose up -d proxy

certs-check:
	curl -s -o /dev/null -w "%{http_code} %{ssl_verify_result}\n" https://localhost/
