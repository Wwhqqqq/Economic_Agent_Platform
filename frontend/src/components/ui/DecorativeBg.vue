<template>
  <div class="decorative-bg" aria-hidden="true">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
    <div class="orb orb-4"></div>
    <div class="grid-pattern"></div>
    <div class="noise"></div>
  </div>
</template>

<style scoped>
.decorative-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(72px);
}

.orb-1 {
  width: 420px;
  height: 420px;
  background: radial-gradient(circle, rgba(167, 139, 250, 0.45) 0%, rgba(167, 139, 250, 0) 70%);
  top: -120px;
  right: 5%;
  animation: float 14s ease-in-out infinite;
}

.orb-2 {
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.35) 0%, rgba(99, 102, 241, 0) 70%);
  bottom: 5%;
  left: 0;
  animation: float 18s ease-in-out infinite reverse;
}

.orb-3 {
  width: 280px;
  height: 280px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.3) 0%, rgba(6, 182, 212, 0) 70%);
  top: 35%;
  right: 30%;
  animation: float 16s ease-in-out infinite;
}

.orb-4 {
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(244, 114, 182, 0.22) 0%, rgba(244, 114, 182, 0) 70%);
  top: 15%;
  left: 25%;
  animation: float 20s ease-in-out infinite reverse;
}

.grid-pattern {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(99, 102, 241, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99, 102, 241, 0.04) 1px, transparent 1px);
  background-size: 40px 40px;
  mask-image: radial-gradient(ellipse 80% 70% at 50% 40%, black 10%, transparent 80%);
}

.noise {
  position: absolute;
  inset: 0;
  opacity: 0.025;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(16px, -20px) scale(1.04); }
  66% { transform: translate(-12px, 10px) scale(0.98); }
}
</style>
