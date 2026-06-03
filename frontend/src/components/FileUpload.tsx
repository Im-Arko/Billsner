import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { api, getErrorMessage } from "../api/client";

const ACCEPT = {
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "application/pdf": [".pdf"],
};

const MAX_SIZE_MB = 20;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

type UploadStatus = "idle" | "uploading" | "success" | "error";

interface FileUploadProps {
  onUploaded?: () => void;
  /** Max number of files per drop (default: unlimited) */
  maxFiles?: number;
}

export function FileUpload({ onUploaded, maxFiles }: FileUploadProps) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [fileCount, setFileCount] = useState(0);

  const onDrop = useCallback(
    async (accepted: File[], rejected: { file: File; errors: { message: string }[] }[]) => {
      if (rejected.length) {
        const reasons = rejected
          .map((r) => `${r.file.name}: ${r.errors.map((e) => e.message).join(", ")}`)
          .join("\n");
        setStatus("error");
        setMessage(reasons);
        return;
      }
      if (!accepted.length) return;

      setStatus("uploading");
      setMessage(null);
      setProgress(5);
      setFileCount(accepted.length);

      const form = new FormData();
      accepted.forEach((f) => form.append("files", f));

      try {
        await api.post("/bills/upload", form, {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (e) => {
            if (e.total) setProgress(Math.round((e.loaded / e.total) * 90) + 5);
          },
        });
        setProgress(100);
        setStatus("success");
        setMessage(`${accepted.length} file${accepted.length > 1 ? "s" : ""} uploaded — processing in background`);
        onUploaded?.();
        // Reset to idle after a moment so the zone is reusable
        setTimeout(() => { setStatus("idle"); setProgress(0); }, 4000);
      } catch (err) {
        setStatus("error");
        setMessage(getErrorMessage(err, "Upload failed"));
      }
    },
    [onUploaded]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPT,
    multiple: true,
    disabled: status === "uploading",
    maxFiles,
    maxSize: MAX_SIZE_BYTES,
  });

  const isActive = isDragActive && !isDragReject;
  const isRejecting = isDragReject;

  return (
    <div>
      <div
        {...getRootProps()}
        className={`dropzone${isActive ? " active" : ""}${isRejecting ? " reject" : ""}${status === "uploading" ? " disabled" : ""}`}
        aria-label="File upload area"
      >
        <input {...getInputProps()} />

        {status === "uploading" ? (
          <>
            <p>Uploading {fileCount} file{fileCount > 1 ? "s" : ""}…</p>
            <p style={{ color: "var(--muted)", fontSize: "0.85rem", marginTop: "0.5rem" }}>
              {progress}%
            </p>
          </>
        ) : isRejecting ? (
          <p style={{ color: "var(--danger, #f87171)" }}>Only JPG, PNG, PDF files under {MAX_SIZE_MB} MB</p>
        ) : (
          <>
            <p>{isDragActive ? "Drop files here…" : "Drag & drop bills (JPG, PNG, PDF)"}</p>
            <p style={{ color: "var(--muted)", fontSize: "0.85rem", marginTop: "0.5rem" }}>
              or click to browse — multiple files supported · max {MAX_SIZE_MB} MB each
            </p>
          </>
        )}
      </div>

      {status === "uploading" && (
        <div className="progress" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
          <div className="progress-bar" style={{ width: `${progress}%`, transition: "width 0.3s ease" }} />
        </div>
      )}

      {message && status !== "uploading" && (
        <p
          style={{
            marginTop: "0.75rem",
            fontSize: "0.875rem",
            color: status === "error" ? "var(--danger, #f87171)" : "var(--muted)",
            whiteSpace: "pre-wrap",
          }}
          role={status === "error" ? "alert" : undefined}
        >
          {status === "success" ? "✓ " : status === "error" ? "✗ " : ""}
          {message}
        </p>
      )}
    </div>
  );
}
