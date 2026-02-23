let secret = randomNumber(1, 100);
let attempts = 0;

const guessInput = document.getElementById("guessInput");
const guessBtn = document.getElementById("guessBtn");
const resetBtn = document.getElementById("resetBtn");
const message = document.getElementById("message");
const attemptsEl = document.getElementById("attempts");

guessBtn.addEventListener("click", handleGuess);
guessInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleGuess();
});
resetBtn.addEventListener("click", resetGame);

function handleGuess() {
  const guess = Number(guessInput.value);

  if (!Number.isInteger(guess) || guess < 1 || guess > 100) {
    setMessage("Please enter a whole number from 1 to 100.");
    return;
  }

  attempts += 1;
  attemptsEl.textContent = attempts;

  if (guess === secret) {
    setMessage(`🎉 Correct! The number was ${secret}. You won in ${attempts} attempts.`);
    guessBtn.disabled = true;
    guessInput.disabled = true;
  } else if (guess < secret) {
    setMessage("Too low. Try a higher number.");
  } else {
    setMessage("Too high. Try a lower number.");
  }

  guessInput.select();
}

function resetGame() {
  secret = randomNumber(1, 100);
  attempts = 0;
  attemptsEl.textContent = attempts;
  guessBtn.disabled = false;
  guessInput.disabled = false;
  guessInput.value = "";
  setMessage("New game started. Make a guess!");
  guessInput.focus();
}

function setMessage(text) {
  message.textContent = text;
}

function randomNumber(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}
