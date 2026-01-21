package main

import (
	"bufio"
	"fmt"
	"math/rand"
	"os"
	"sync"
	"time"
)

const (
	logFileName = "logs.log"
	maxLines    = 200
)

var (
	logLevels = []string{"DEBUG", "INFO", "ERROR"}
	mu        sync.Mutex
)

func main() {
	rand.Seed(time.Now().UnixNano())

	go func() {
		for {
			generateLog()
			time.Sleep(time.Millisecond * 100)
		}
	}()

	select {}
}

func generateLog() {
	mu.Lock()
	defer mu.Unlock()

	lines, err := readLines(logFileName)
	if err != nil {
		fmt.Println("Error reading log file:", err)
		return
	}

	if len(lines) >= maxLines {
		lines = lines[len(lines)-maxLines+1:]
	}

	logLine := fmt.Sprintf("%s [%s] %s\n", time.Now().Format(time.RFC3339), logLevels[rand.Intn(len(logLevels))], generateRandomMessage())
	lines = append(lines, logLine)

	err = writeLines(lines, logFileName)
	if err != nil {
		fmt.Println("Error writing to log file:", err)
	}
}

func generateRandomMessage() string {
	messages := []string{
		"User logged in",
		"File uploaded",
		"Error processing request",
		"User logged out",
		"Database connection established",
		"Invalid input received",
	}
	return messages[rand.Intn(len(messages))]
}

func readLines(fileName string) ([]string, error) {
	file, err := os.Open(fileName)
	if os.IsNotExist(err) {
		return []string{}, nil
	} else if err != nil {
		return nil, err
	}
	defer file.Close()

	var lines []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	return lines, scanner.Err()
}

func writeLines(lines []string, fileName string) error {
	file, err := os.Create(fileName)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := bufio.NewWriter(file)
	for _, line := range lines {
		fmt.Fprintln(writer, line)
	}
	return writer.Flush()
}
