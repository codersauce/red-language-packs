<script setup lang="ts">
const greeting: string = "Hello from Red!"
</script>

<template>
  <h1 v-if="greeting" class="greeting">{{ greeting }}</h1>
</template>

<style scoped>
.greeting { color: red; }
</style>
