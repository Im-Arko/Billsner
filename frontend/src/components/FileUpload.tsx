import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { api } from "../api/client";

const ACCEPT = {
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "application/pdf": [".pdf"],
};

export function FileUpload({ onUploaded }: { onUploaded?: () => void }) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback(
    async (accepted: File[]) => {
      if (!accepted.length) return;
      setUploading(true);
      setStatus(null);
      setProgress(10);
      const form = new FormData();
      accepted.forEach((f) => form.append("files", f));
      try {
        await api.post("/bills/upload", form, {
          headers: { "Content-Type": "multipart/form-data" },
          onUploadProgress: (e) => {
            if (e.total) setProgress(Math.round((e.loaded / e.total) * 100));
          },
        });
        setStatus(`${accepted.length} file(s) uploaded — processing in background`);
        setProgress(100);
        onUploaded?.();
      } catch (err: unknown) {
        const msg =
          err && typeof err === "object" && "response" in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data
                ?.detail
            : "Upload failed";
        setStatus(String(msg));
      } finally {
        setUploading(false);
      }
    },
    [onUploaded]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    multiple: true,
    disabled: uploading,
  });

  return (
    <div>
      <div {...getRootProps()} className={`dropzone ${isDragActive ? "active" : ""}`}>
        <input {...getInputProps()} />
        <p>{isDragActive ? "Drop files here…" : "Drag & drop bills (JPG, PNG, PDF)"}</p>
        <p style={{ color: "var(--muted)", fontSize: "0.85rem", marginTop: "0.5rem" }}>
          or click to browse — multiple files supported
        </p>
      </div>
      {uploading && (
        <div className="progress">
          <div className="progress-bar" style={{ width: `${progress}%` }} />
        </div>
      )}
      {status && (
        <p style={{ marginTop: "0.75rem", color: "var(--muted)", fontSize: "0.9rem" }}>
          {status}
        </p>
      )}
    </div>
  );
}
