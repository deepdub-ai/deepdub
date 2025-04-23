all: clean build upload

build:
	uv build

upload:
	twine upload dist/*

clean:
	rm dist/*

