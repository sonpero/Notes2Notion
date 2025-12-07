"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useAuth } from "../hooks/useAuth";

interface CameraCaptureProps {
  testMode: boolean;
}

type StatusType = "success" | "error" | "info" | null;

export default function CameraCapture({ testMode }: CameraCaptureProps) {
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [showDesktopMenu, setShowDesktopMenu] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [status, setStatus] = useState<{ message: string; type: StatusType }>({
    message: "",
    type: null,
  });

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001";

  // Get refreshUser from auth context to sync state after errors
  const { refreshUser } = useAuth();

  // Detect if device is mobile
  useEffect(() => {
    const checkMobile = () => {
      const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera;
      const mobileCheck = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent.toLowerCase());
      const touchCheck = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      setIsMobile(mobileCheck || touchCheck);
    };
    checkMobile();
  }, []);

  const showStatus = useCallback((message: string, type: StatusType) => {
    setStatus({ message, type });
  }, []);

  const startCamera = async () => {
    try {
      // Check if page is served over HTTPS (required for camera access on mobile)
      if (window.location.protocol === "http:" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
        showStatus("Erreur: La caméra nécessite HTTPS sur mobile. Utilisez 'Choisir une photo' à la place.", "error");
        return;
      }

      // Check if getUserMedia is supported
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showStatus("Erreur: Votre navigateur ne supporte pas l'accès à la caméra. Utilisez 'Choisir une photo' à la place.", "error");
        return;
      }

      showStatus("Demande d'accès à la caméra...", "info");

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        },
      });

      streamRef.current = stream;
      setIsCameraActive(true);
      showStatus("", null);

      // Use setTimeout to ensure React has rendered the video element
      setTimeout(() => {
        if (videoRef.current && streamRef.current) {
          videoRef.current.srcObject = streamRef.current;

          // Wait for video to be ready and play
          videoRef.current.onloadedmetadata = () => {
            videoRef.current?.play().catch((err: unknown) => {
              console.error("Error playing video:", err);
            });
          };
        }
      }, 100);
    } catch (err) {
      console.error("Camera error:", err);
      if (err instanceof Error) {
        if (err.name === "NotAllowedError") {
          showStatus("Erreur: Permission caméra refusée. Autorisez l'accès dans les paramètres de votre navigateur.", "error");
        } else if (err.name === "NotFoundError") {
          showStatus("Erreur: Aucune caméra trouvée sur cet appareil.", "error");
        } else if (err.name === "NotSupportedError" || err.name === "TypeError") {
          showStatus("Erreur: La caméra nécessite HTTPS. Utilisez 'Choisir une photo' à la place.", "error");
        } else {
          showStatus(`Erreur caméra: ${err.message}. Utilisez 'Choisir une photo' à la place.`, "error");
        }
      } else {
        showStatus("Erreur: Impossible d'accéder à la caméra. Utilisez 'Choisir une photo' à la place.", "error");
      }
    }
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.drawImage(video, 0, 0);

        canvas.toBlob(
          (blob) => {
            if (blob) {
              setCapturedBlob(blob);
              setCapturedImage(URL.createObjectURL(blob));
              setIsCameraActive(false);

              // Stop camera
              if (streamRef.current) {
                streamRef.current.getTracks().forEach((track) => track.stop());
                streamRef.current = null;
              }
            }
          },
          "image/jpeg",
          0.9
        );
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setCapturedBlob(file);
      setCapturedImage(URL.createObjectURL(file));
      setStatus({ message: "", type: null });
    }
  };

  const retakePhoto = () => {
    setCapturedImage(null);
    setCapturedBlob(null);
    setStatus({ message: "", type: null });
    setShowDesktopMenu(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleAddPhotoClick = () => {
    if (isMobile) {
      // On mobile, directly open the native file picker (which includes camera option)
      fileInputRef.current?.click();
    } else {
      // On desktop, show custom menu
      setShowDesktopMenu(true);
    }
  };

  const handleDesktopCameraClick = () => {
    setShowDesktopMenu(false);
    startCamera();
  };

  const handleDesktopFileClick = () => {
    setShowDesktopMenu(false);
    // Use setTimeout to ensure the menu is closed before opening file picker
    setTimeout(() => {
      fileInputRef.current?.click();
    }, 50);
  };

  const uploadToNotion = async () => {
    if (!capturedBlob) return;

    setIsUploading(true);
    showStatus("Upload et traitement en cours...", "info");

    const formData = new FormData();
    formData.append("photo", capturedBlob, "note.jpg");
    formData.append("test_mode", testMode.toString());

    // Get session token from localStorage (OAuth token)
    const sessionToken = localStorage.getItem("notes2notion_session_token");

    try {
      const headers: HeadersInit = {};
      if (sessionToken) {
        headers["Authorization"] = `Bearer ${sessionToken}`;
      }

      // Use relative URL to call Next.js API proxy instead of direct backend call
      const response = await fetch('/api/upload', {
        method: "POST",
        headers,
        body: formData,
      });

      const result = await response.json();

      if (response.status === 401) {
        // Unauthorized - could be expired session or failed token refresh
        // The backend message will tell us which one
        const errorMessage = result.message || "Session expirée. Rechargez la page pour vous reconnecter.";
        showStatus(`❌ ${errorMessage}`, "error");

        // Only clear token and force reload if it's an auth failure
        // (token refresh failed means the refresh_token is also invalid)
        if (result.error === 'Authentication failed') {
          localStorage.removeItem("notes2notion_session_token");
          setTimeout(() => {
            window.location.reload();
          }, 3000);
        }
        return;
      }

      if (response.status === 400 && result.error === 'No default page configured') {
        // User hasn't configured page ID
        showStatus(`❌ Aucune page Notion configurée. Configurez votre page par défaut.`, "error");
        // Trigger page setup - the parent component will handle this
        window.location.reload();
        return;
      }

      if (response.status === 410 && result.error === 'page_deleted') {
        // Page was deleted - backend has already cleared the page_id
        // Show message and refresh user state from backend
        showStatus(`❌ ${result.message}`, "error");

        // Refresh user state from backend (will update has_page_id to false)
        await refreshUser();

        // Reload to trigger page setup flow
        setTimeout(() => {
          window.location.reload();
        }, 2000);
        return;
      }

      if (result.success) {
        const modeLabel = testMode ? " (Mode Test)" : "";
        showStatus(`✅ Notes envoyées vers Notion avec succès!${modeLabel}`, "success");

        // Reset after 3 seconds
        setTimeout(() => {
          retakePhoto();
        }, 3000);
      } else {
        // Display backend error message if available, otherwise use generic error
        const errorMessage = result.message || result.error || "Erreur inconnue";
        showStatus(`❌ ${errorMessage}`, "error");
      }
    } catch (err) {
      showStatus(`❌ Erreur réseau: ${err instanceof Error ? err.message : "Unknown error"}`, "error");
      console.error(err);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Camera/Canvas/Preview Container */}
      <div className="relative">
        {isCameraActive && (
          <div className="relative w-full h-64 bg-black rounded-xl overflow-hidden">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="absolute inset-0 w-full h-full object-cover"
            />
          </div>
        )}

        <canvas ref={canvasRef} className="hidden" />

        {capturedImage && (
          <img
            src={capturedImage}
            alt="Preview"
            className="w-full rounded-xl"
          />
        )}

        {!isCameraActive && !capturedImage && (
          <div className="w-full h-64 bg-gray-100 rounded-xl flex items-center justify-center">
            <p className="text-gray-400 text-sm">Aucune photo</p>
          </div>
        )}
      </div>

      {/* Buttons */}
      <div className="space-y-3">
        {!isCameraActive && !capturedImage && !showDesktopMenu && (
          <>
            <button onClick={handleAddPhotoClick} className="w-full btn-gradient">
              <span className="mr-2">📸</span>
              Ajouter une photo
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
            />
          </>
        )}

        {/* Desktop Menu */}
        {showDesktopMenu && !isCameraActive && !capturedImage && (
          <div className="space-y-2">
            <button
              onClick={handleDesktopCameraClick}
              className="w-full btn-gradient"
            >
              <span className="mr-2">📷</span>
              Capturer avec la webcam
            </button>
            <button
              onClick={handleDesktopFileClick}
              className="w-full btn-secondary"
            >
              <span className="mr-2">📁</span>
              Choisir un fichier
            </button>
            <button
              onClick={() => setShowDesktopMenu(false)}
              className="w-full btn-secondary text-sm"
            >
              Annuler
            </button>
          </div>
        )}

        {isCameraActive && (
          <button onClick={capturePhoto} className="w-full btn-gradient">
            <span className="mr-2">📸</span>
            Prendre la photo
          </button>
        )}

        {capturedImage && (
          <>
            <button
              onClick={retakePhoto}
              className="w-full btn-secondary"
              disabled={isUploading}
            >
              <span className="mr-2">🔄</span>
              Reprendre
            </button>

            <button
              onClick={uploadToNotion}
              className="w-full btn-success"
              disabled={isUploading}
            >
              {isUploading ? (
                <>
                  <span className="loading-spinner mr-2"></span>
                  Envoi en cours...
                </>
              ) : (
                <>
                  <span className="mr-2">☁️</span>
                  Envoyer vers Notion
                </>
              )}
            </button>
          </>
        )}
      </div>

      {/* Status Message */}
      {status.type && (
        <div className={`status-${status.type}`}>
          {status.message}
        </div>
      )}
    </div>
  );
}
