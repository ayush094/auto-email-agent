import { useEffect, useMemo, useState } from "react";
import axios from "axios";

const toneOptions = ["professional", "friendly", "apologetic", "assertive"];

const toneRequestMap = {
  professional: "professional",
  friendly: "friendly",
  apologetic: "formal",
  assertive: "professional",
};

const fallbackEmails = [
  {
    id: "demo-1",
    sender: "Priya Sharma",
    sender_email: "priya@example.com",
    subject: "Order delayed and no shipping update",
    preview: "I placed my order three days ago and still have not received a tracking link.",
    email_content:
      "Hi team,\n\nI placed my order three days ago and still have not received a tracking link. Could you please check the shipment status and let me know when I can expect delivery?\n\nThanks,\nPriya",
    company_name: "Acme Support",
    received_at: "Demo",
    status: "pending",
    aiReply: "",
    deliveryStatus: "draft",
  },
];

const filters = [
  { id: "all", label: "All Mail" },
  { id: "received", label: "Received" },
  { id: "pending", label: "Pending" },
  { id: "replied", label: "AI Replied" },
];

const statusStyles = {
  received: "bg-sky-50 text-sky-700 ring-sky-200",
  pending: "bg-amber-50 text-amber-700 ring-amber-200",
  replied: "bg-emerald-50 text-emerald-700 ring-emerald-200",
};

const deliveryStatusStyles = {
  draft: "bg-slate-100 text-slate-600",
  ready: "bg-violet-100 text-violet-700",
  sent: "bg-emerald-100 text-emerald-700",
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

function buildFormFromEmail(email) {
  return {
    email_content: email?.email_content || "",
    sender_name: email?.sender || "",
    company_name: email?.company_name || "Acme Support",
    tone_preference: "professional",
  };
}

function normalizeInboxEmails(emails) {
  return emails.map((email) => ({
    ...email,
    company_name: email.company_name || "Acme Support",
    status: email.status || "received",
    aiReply: email.aiReply || "",
    deliveryStatus: email.deliveryStatus || "draft",
  }));
}

function buildEmailKey(email) {
  return `${(email.sender_email || "").toLowerCase()}::${(email.subject || "").toLowerCase()}`;
}

function mergeInboxEmails(existingEmails, incomingEmails) {
  const existingById = new Map(existingEmails.map((email) => [String(email.id), email]));
  const existingByKey = new Map(existingEmails.map((email) => [buildEmailKey(email), email]));

  return incomingEmails.map((email) => {
    const preserved = existingById.get(String(email.id)) || existingByKey.get(buildEmailKey(email));

    if (!preserved) {
      return email;
    }

    const hasDraft = Boolean(preserved.aiReply);
    return {
      ...email,
      aiReply: preserved.aiReply || email.aiReply || "",
      status: hasDraft ? "replied" : preserved.status || email.status,
      preview: hasDraft ? preserved.preview || email.preview : email.preview,
      deliveryStatus: preserved.deliveryStatus || email.deliveryStatus || "draft",
    };
  });
}

function App() {
  const [emails, setEmails] = useState(fallbackEmails);
  const [activeFilter, setActiveFilter] = useState("all");
  const [selectedEmailId, setSelectedEmailId] = useState(fallbackEmails[0].id);
  const [formData, setFormData] = useState(buildFormFromEmail(fallbackEmails[0]));
  const [error, setError] = useState("");
  const [banner, setBanner] = useState("");
  const [loadingReply, setLoadingReply] = useState(false);
  const [loadingInbox, setLoadingInbox] = useState(false);
  const [sendingReply, setSendingReply] = useState(false);
  const [copied, setCopied] = useState(false);

  const selectedEmail = useMemo(
    () => emails.find((email) => email.id === selectedEmailId) ?? emails[0],
    [emails, selectedEmailId],
  );

  const filteredEmails = useMemo(() => {
    if (activeFilter === "all") {
      return emails;
    }

    return emails.filter((email) => email.status === activeFilter);
  }, [activeFilter, emails]);

  const stats = useMemo(
    () => ({
      all: emails.length,
      received: emails.filter((email) => email.status === "received").length,
      pending: emails.filter((email) => email.status === "pending").length,
      replied: emails.filter((email) => email.status === "replied").length,
    }),
    [emails],
  );

  useEffect(() => {
    setFormData(buildFormFromEmail(selectedEmail));
    setError("");
    setCopied(false);
  }, [selectedEmail]);

  useEffect(() => {
    if (!copied) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => setCopied(false), 1800);
    return () => window.clearTimeout(timeoutId);
  }, [copied]);

  useEffect(() => {
    if (!banner) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => setBanner(""), 2600);
    return () => window.clearTimeout(timeoutId);
  }, [banner]);

  useEffect(() => {
    const loadInbox = async () => {
      setLoadingInbox(true);
      setError("");

      try {
        const response = await api.get("/inbox-emails/");
        const inboxEmails = normalizeInboxEmails(response.data?.emails || []);

        if (inboxEmails.length) {
          setEmails((current) => {
            const mergedEmails = mergeInboxEmails(current, inboxEmails);
            setSelectedEmailId((currentSelectedId) =>
              mergedEmails.some((email) => email.id === currentSelectedId)
                ? currentSelectedId
                : mergedEmails[0].id,
            );
            return mergedEmails;
          });
          setBanner("Live Gmail content loaded into the dashboard.");
        } else {
          setBanner("No inbox emails found. Showing the dashboard with an empty inbox.");
          setEmails([]);
          setSelectedEmailId("");
        }
      } catch (requestError) {
        const message = requestError.response?.data?.error || "";
        setError(message || "Unable to load Gmail inbox. Showing demo content instead.");
        setEmails(fallbackEmails);
        setSelectedEmailId(fallbackEmails[0].id);
      } finally {
        setLoadingInbox(false);
      }
    };

    loadInbox();
  }, []);

  const handleSelectEmail = (email) => {
    setSelectedEmailId(email.id);
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const handleLoadInbox = async () => {
    if (loadingInbox) {
      return;
    }

    setLoadingInbox(true);
    setError("");
    setBanner("");

    try {
      const inboxResponse = await api.get("/inbox-emails/");
      const inboxEmails = normalizeInboxEmails(inboxResponse.data?.emails || []);

      setEmails((current) => {
        const mergedEmails = mergeInboxEmails(current, inboxEmails);
        if (mergedEmails.length) {
          setSelectedEmailId((currentSelectedId) =>
            mergedEmails.some((email) => email.id === currentSelectedId)
              ? currentSelectedId
              : mergedEmails[0].id,
          );
        }
        return mergedEmails;
      });
      setBanner("Inbox refreshed. Drafts stay in review until you confirm sending.");
    } catch (requestError) {
      const message = requestError.response?.data?.error || "";
      setError(message || "Inbox load failed. Please check the backend email configuration.");
    } finally {
      setLoadingInbox(false);
    }
  };

  const handleGenerateReply = async (event) => {
    event.preventDefault();
    if (loadingReply || !selectedEmail) {
      return;
    }

    setLoadingReply(true);
    setError("");
    setBanner("");
    setCopied(false);

    try {
      const payload = {
        ...formData,
        tone_preference: toneRequestMap[formData.tone_preference] ?? "professional",
      };

      const response = await api.post("/generate-reply/", payload);
      const generatedReply = response.data.reply || "";

      setEmails((current) =>
        current.map((email) =>
          email.id === selectedEmail.id
            ? {
                ...email,
                status: "replied",
                aiReply: generatedReply,
                preview: generatedReply.split("\n")[0],
                deliveryStatus: "ready",
              }
            : email,
        ),
      );

      setBanner("AI drafted a reply. Review it and click Send Reply only if you approve.");
    } catch (requestError) {
      const message =
        requestError.response?.data?.error ||
        requestError.response?.data?.tone_preference?.[0] ||
        requestError.response?.data?.email_content?.[0] ||
        "Unable to generate a reply right now. Please try again.";

      setError(message);
    } finally {
      setLoadingReply(false);
    }
  };

  const handleSendReply = async () => {
    if (!selectedEmail?.aiReply || sendingReply) {
      return;
    }

    const approved = window.confirm(
      `Send this AI reply to ${selectedEmail.sender_email}?`,
    );

    if (!approved) {
      return;
    }

    setSendingReply(true);
    setError("");
    setBanner("");

    try {
      await api.post("/send-approved-reply/", {
        recipient_email: selectedEmail.sender_email,
        subject: selectedEmail.subject,
        reply_text: selectedEmail.aiReply,
      });

      setEmails((current) =>
        current.map((email) =>
          email.id === selectedEmail.id
            ? {
                ...email,
                deliveryStatus: "sent",
              }
            : email,
        ),
      );

      setBanner("Approved reply sent successfully.");
    } catch (requestError) {
      const message = requestError.response?.data?.error || "";
      setError(message || "Failed to send the approved reply.");
    } finally {
      setSendingReply(false);
    }
  };

  const handleCopy = async () => {
    if (!selectedEmail?.aiReply) {
      return;
    }

    try {
      await navigator.clipboard.writeText(selectedEmail.aiReply);
      setCopied(true);
    } catch {
      setError("Copy failed. Please copy the reply manually.");
    }
  };

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,_#eef3fb_0%,_#f7f9fc_38%,_#edf2f8_100%)] text-slate-900">
      <div className="mx-auto max-w-[1680px] px-4 py-5 sm:px-6 lg:px-8">
        <header className="mb-5 rounded-[32px] border border-white/70 bg-white/80 px-5 py-5 shadow-[0_24px_60px_rgba(15,23,42,0.08)] backdrop-blur sm:px-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-[22px] bg-[linear-gradient(135deg,_#ea4335,_#1a73e8)] text-base font-bold text-white shadow-lg">
                AI
              </div>
              <div>
                <h1 className="font-['Plus_Jakarta_Sans'] text-3xl font-semibold tracking-tight text-slate-950">
                  AI Email Assistant
                </h1>
                <p className="mt-1 text-sm text-slate-500">
                  Read Gmail, draft smart replies, then send only after your approval
                </p>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-slate-50 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Received</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{stats.received}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Pending</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{stats.pending}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-400">AI Replied</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{stats.replied}</p>
              </div>
            </div>
          </div>
        </header>

        <div className="grid gap-5 xl:grid-cols-[250px_420px_minmax(520px,1fr)]">
          <aside className="rounded-[30px] border border-white/70 bg-white/85 p-4 shadow-[0_24px_60px_rgba(15,23,42,0.08)] backdrop-blur">
            <button
              type="button"
              onClick={handleLoadInbox}
              disabled={loadingInbox}
              className="mb-6 flex w-full items-center justify-center gap-2 rounded-[22px] bg-[#d93025] px-4 py-3.5 text-sm font-semibold text-white shadow-[0_12px_30px_rgba(217,48,37,0.25)] transition hover:-translate-y-0.5 hover:bg-[#c5221f] disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loadingInbox ? (
                <>
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Loading Gmail
                </>
              ) : (
                "Load My Gmail"
              )}
            </button>

            <nav className="space-y-2.5">
              {filters.map((filter) => {
                const isActive = activeFilter === filter.id;
                const count = stats[filter.id];

                return (
                  <button
                    key={filter.id}
                    type="button"
                    onClick={() => setActiveFilter(filter.id)}
                    className={`flex w-full items-center justify-between rounded-[20px] px-4 py-3 text-left transition ${
                      isActive
                        ? "bg-[#e8f0fe] text-[#174ea6] shadow-sm"
                        : "text-slate-600 hover:bg-slate-100"
                    }`}
                  >
                    <span className="font-medium">{filter.label}</span>
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs ${
                        isActive ? "bg-white text-[#174ea6]" : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </nav>

            <div className="mt-6 rounded-[24px] bg-[linear-gradient(180deg,_#0f172a,_#1e293b)] p-5 text-white shadow-[0_20px_40px_rgba(15,23,42,0.18)]">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Review Flow</p>
              <p className="mt-3 text-sm leading-6 text-slate-200">
                Gmail is read-only here. The AI drafts a response first, and nothing is sent until
                you explicitly confirm it.
              </p>
            </div>
          </aside>

          <section className="rounded-[30px] border border-white/70 bg-white/85 shadow-[0_24px_60px_rgba(15,23,42,0.08)] backdrop-blur">
            <div className="border-b border-slate-200/80 px-5 py-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Inbox</p>
                  <h2 className="mt-2 font-['Plus_Jakarta_Sans'] text-2xl font-semibold text-slate-950">
                    Message Queue
                  </h2>
                </div>
                <div className="rounded-full bg-slate-100 px-3 py-1.5 text-xs text-slate-500">
                  {loadingInbox ? "Loading..." : `${filteredEmails.length} threads`}
                </div>
              </div>
            </div>

            <div className="space-y-3 p-4">
              {filteredEmails.length ? (
                filteredEmails.map((email) => {
                  const isSelected = email.id === selectedEmailId;

                  return (
                    <button
                      key={email.id}
                      type="button"
                      onClick={() => handleSelectEmail(email)}
                      className={`w-full rounded-[26px] border px-4 py-4 text-left transition ${
                        isSelected
                          ? "border-[#bfd4ff] bg-[#eef4ff] shadow-[0_10px_24px_rgba(26,115,232,0.10)]"
                          : "border-slate-200/70 bg-white hover:border-slate-300 hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[18px] bg-slate-900 text-sm font-semibold text-white">
                          {email.sender.slice(0, 2).toUpperCase()}
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="truncate text-sm font-semibold text-slate-900">{email.sender}</p>
                            <span
                              className={`rounded-full px-2.5 py-1 text-[11px] font-medium capitalize ring-1 ${statusStyles[email.status]}`}
                            >
                              {email.status}
                            </span>
                            {email.aiReply ? (
                              <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${deliveryStatusStyles[email.deliveryStatus || "draft"]}`}>
                                {email.deliveryStatus === "sent" ? "sent" : "draft ready"}
                              </span>
                            ) : null}
                            <span className="text-xs text-slate-400">{email.received_at}</span>
                          </div>
                          <p className="mt-2 truncate text-sm font-medium text-slate-800">{email.subject}</p>
                          <p className="mt-1 line-clamp-2 text-sm leading-6 text-slate-500">
                            {email.preview}
                          </p>
                          {email.aiReply ? (
                            <div className="mt-3 rounded-2xl bg-emerald-50 px-3 py-2 text-xs leading-5 text-emerald-700">
                              AI draft: {email.aiReply.split("\n")[0]}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </button>
                  );
                })
              ) : (
                <div className="rounded-[26px] border border-dashed border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-500">
                  No emails available to show.
                </div>
              )}
            </div>
          </section>

          <section className="rounded-[30px] border border-white/70 bg-white/90 shadow-[0_24px_60px_rgba(15,23,42,0.08)] backdrop-blur">
            <div className="border-b border-slate-200/80 px-6 py-5">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Conversation</p>
                  <h2 className="mt-2 font-['Plus_Jakarta_Sans'] text-2xl font-semibold text-slate-950">
                    {selectedEmail?.subject || "Select an email"}
                  </h2>
                  <p className="mt-2 text-sm text-slate-500">
                    {selectedEmail ? `From ${selectedEmail.sender} | ${selectedEmail.sender_email}` : "No email selected"}
                  </p>
                </div>

                {selectedEmail ? (
                  <div className="flex flex-wrap items-center gap-3">
                    <span
                      className={`inline-flex rounded-full px-3 py-1.5 text-xs font-semibold capitalize ring-1 ${statusStyles[selectedEmail.status || "received"]}`}
                    >
                      {selectedEmail.status}
                    </span>
                    {selectedEmail.aiReply ? (
                      <span className={`rounded-full px-3 py-1.5 text-xs font-semibold ${deliveryStatusStyles[selectedEmail.deliveryStatus || "draft"]}`}>
                        {selectedEmail.deliveryStatus === "sent" ? "Sent to user" : "Waiting for approval"}
                      </span>
                    ) : null}
                    <button
                      type="button"
                      onClick={handleCopy}
                      disabled={!selectedEmail.aiReply}
                      className="rounded-[18px] border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Copy AI Reply
                    </button>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="grid gap-6 p-6 2xl:grid-cols-[minmax(0,1.15fr)_360px]">
              <div className="space-y-5">
                <article className="rounded-[28px] bg-[#f8fafc] p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-[18px] bg-white text-sm font-semibold text-slate-900 shadow-sm">
                      {selectedEmail?.sender?.slice(0, 2).toUpperCase() || "--"}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{selectedEmail?.sender || "No sender"}</p>
                      <p className="text-xs text-slate-500">{selectedEmail?.sender_email || ""}</p>
                    </div>
                  </div>
                  <div className="mt-4 rounded-[24px] bg-white px-5 py-4 shadow-sm">
                    <p className="whitespace-pre-wrap text-sm leading-7 text-slate-600">
                      {selectedEmail?.email_content || "Select an email to see its content."}
                    </p>
                  </div>
                </article>

                <article className="rounded-[28px] bg-[linear-gradient(180deg,_#0f172a,_#162338)] p-5 text-white shadow-[0_20px_45px_rgba(15,23,42,0.18)]">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-[18px] bg-[#1a73e8] text-sm font-semibold text-white">
                      AI
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">AI Responder</p>
                      <p className="text-xs text-slate-300">Draft first, send only after your approval</p>
                    </div>
                  </div>
                  <div className="mt-4 rounded-[24px] bg-white/8 px-5 py-4">
                    {selectedEmail?.aiReply ? (
                      <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-7 text-slate-100">
                        {selectedEmail.aiReply}
                      </pre>
                    ) : (
                      <div className="py-10 text-center">
                        <p className="text-lg font-medium text-white">No AI reply yet</p>
                        <p className="mt-2 text-sm leading-6 text-slate-300">
                          Generate a response and review it here before deciding whether to send it.
                        </p>
                      </div>
                    )}
                  </div>
                </article>
              </div>

              <aside className="rounded-[28px] bg-[#f8fafc] p-5">
                <div className="mb-5">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Compose Panel</p>
                  <h3 className="mt-2 font-['Plus_Jakarta_Sans'] text-xl font-semibold text-slate-950">
                    Understand and Draft
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    The AI now focuses on the actual meaning of the email and drafts a response for your review.
                  </p>
                </div>

                <form className="space-y-4" onSubmit={handleGenerateReply}>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-slate-700">Email Content</span>
                    <textarea
                      name="email_content"
                      value={formData.email_content}
                      onChange={handleChange}
                      rows={6}
                      className="w-full rounded-[22px] border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-800 outline-none transition focus:border-[#8ab4f8] focus:ring-4 focus:ring-[#e8f0fe]"
                      placeholder="Paste the email you received..."
                      required
                      disabled={!selectedEmail}
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-slate-700">Sender Name</span>
                    <input
                      type="text"
                      name="sender_name"
                      value={formData.sender_name}
                      onChange={handleChange}
                      className="w-full rounded-[22px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-[#8ab4f8] focus:ring-4 focus:ring-[#e8f0fe]"
                      disabled={!selectedEmail}
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-slate-700">Company Name</span>
                    <input
                      type="text"
                      name="company_name"
                      value={formData.company_name}
                      onChange={handleChange}
                      className="w-full rounded-[22px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-[#8ab4f8] focus:ring-4 focus:ring-[#e8f0fe]"
                      disabled={!selectedEmail}
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-slate-700">Tone</span>
                    <select
                      name="tone_preference"
                      value={formData.tone_preference}
                      onChange={handleChange}
                      className="w-full rounded-[22px] border border-slate-200 bg-white px-4 py-3 text-sm capitalize text-slate-800 outline-none transition focus:border-[#8ab4f8] focus:ring-4 focus:ring-[#e8f0fe]"
                      disabled={!selectedEmail}
                    >
                      {toneOptions.map((tone) => (
                        <option key={tone} value={tone}>
                          {tone}
                        </option>
                      ))}
                    </select>
                    <p className="mt-2 text-xs leading-5 text-slate-500">
                      Apologetic and assertive are adapted to the closest backend-supported tone.
                    </p>
                  </label>

                  <button
                    type="submit"
                    disabled={loadingReply || !selectedEmail}
                    className="flex w-full items-center justify-center gap-2 rounded-[22px] bg-[#1a73e8] px-5 py-3.5 text-sm font-semibold text-white shadow-[0_14px_30px_rgba(26,115,232,0.22)] transition hover:-translate-y-0.5 hover:bg-[#1765cc] disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {loadingReply ? (
                      <>
                        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                        Drafting reply
                      </>
                    ) : (
                      "Generate AI Draft"
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={handleSendReply}
                    disabled={!selectedEmail?.aiReply || sendingReply}
                    className="flex w-full items-center justify-center gap-2 rounded-[22px] border border-slate-300 bg-white px-5 py-3.5 text-sm font-semibold text-slate-800 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {sendingReply ? (
                      <>
                        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
                        Sending approved reply
                      </>
                    ) : (
                      "Send Reply (After Yes)"
                    )}
                  </button>
                </form>

                <div className="mt-5 space-y-3">
                  {error ? (
                    <div className="rounded-[22px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                      {error}
                    </div>
                  ) : null}
                  {banner ? (
                    <div className="rounded-[22px] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                      {banner}
                    </div>
                  ) : null}
                  {copied ? (
                    <div className="rounded-[22px] border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-700">
                      AI reply copied to clipboard.
                    </div>
                  ) : null}
                </div>
              </aside>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

export default App;
