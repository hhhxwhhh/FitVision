<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>

<style>
/* 全局重置样式，去掉浏览器默认的白边 */
body {
  margin: 0;
  padding: 0;
}
</style>