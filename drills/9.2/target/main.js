function clamp(x, lo, hi) {
  return Math.min(Math.max(x, lo), hi);
}
const speed = clamp(input, 0, 120);
console.log(speed);
