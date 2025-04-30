// static/firebase-auth.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.0.0/firebase-app.js";
import { getAuth, signInWithEmailAndPassword } from "https://www.gstatic.com/firebasejs/9.0.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyAQV5MnRUHc27kzldAOVHgdipxz20FulqE",
  authDomain: "true-mail.firebaseapp.com",
  projectId: "true-mail",
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const idToken = await userCredential.user.getIdToken();

    const response = await fetch("http://localhost:8000/auth/firebase-login", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${idToken}`,
        "Content-Type": "application/json"
      }
    });

    const result = await response.json();
    alert("Login success: " + JSON.stringify(result));
  } catch (error) {
    alert("Login failed: " + error.message);
  }
});

