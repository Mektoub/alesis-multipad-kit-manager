<script>
  let { colors, value = $bindable(), label } = $props();
</script>

<div class="swatches" role="radiogroup" aria-label={label}>
  {#each colors as c, i (c.name)}
    <button
      type="button"
      role="radio"
      aria-checked={value === i}
      class:selected={value === i}
      style:background={c.css}
      title={c.name}
      aria-label={c.name}
      onclick={() => (value = i)}
    ></button>
  {/each}
</div>

<style>
  .swatches {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  button {
    width: 22px;
    height: 22px;
    padding: 0;
    border-radius: 50%;
    border: 2px solid var(--border);
  }
  button.selected {
    border-color: var(--text);
    box-shadow: 0 0 0 2px var(--panel), 0 0 0 4px var(--text);
  }
</style>
