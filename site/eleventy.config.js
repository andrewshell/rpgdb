export default function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("src/covers");
  eleventyConfig.addPassthroughCopy("src/search.js");
  return { dir: { input: "src", output: "_site" } };
}
