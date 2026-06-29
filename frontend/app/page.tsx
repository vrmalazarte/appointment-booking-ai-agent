"use client";

import { FormEvent, useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi! I can help you book an appointment. Ask me what slots are available.",
    },
  ]);

  const [input, setInput] = useState("");

  function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const userMessage = input.trim();

    if (!userMessage) {
      return;
    }

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        role: "user",
        content: userMessage,
      },
      {
        role: "assistant",
        content:
          "Frontend is working. Later, this reply will come from the AI Agent backend.",
      },
    ]);

    setInput("");
  }

  return (
    <main className="page">
      <section className="chatBox">
        <header className="header">
          <p className="label">AI Booking Agent</p>
          <h1>Appointment Booking Assistant</h1>
          <p className="description">
            Chat with an AI assistant to check appointment slots and book a
            schedule.
          </p>
        </header>

        <div className="messages">
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              {message.content}
            </div>
          ))}
        </div>

        <form className="form" onSubmit={sendMessage}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask for available slots..."
          />
          <button type="submit">Send</button>
        </form>
      </section>
    </main>
  );
}