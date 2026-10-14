export default function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("src/covers");
  eleventyConfig.addPassthroughCopy("src/icons");
  eleventyConfig.addPassthroughCopy("src/search.js");

  // A new version on every build makes phones replace their offline copy after each publish.
  const builtAt = new Date();
  eleventyConfig.addGlobalData("build", {
    version: builtAt.getTime().toString(36),
    date: builtAt.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" }),
  });

  return { dir: { input: "src", output: "_site" } };
}
