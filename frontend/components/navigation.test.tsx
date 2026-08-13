import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Home from "@/app/page";
import { SiteFooter } from "./SiteFooter";
import { SiteHeader } from "./SiteHeader";

describe("public navigation", () => {
  it("uses consistent product branding and working header routes", () => {
    render(<SiteHeader />);

    expect(screen.getByRole("link", { name: "Paani Bachao home" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Assessment" })).toHaveAttribute("href", "/assessment");
    expect(screen.getByRole("link", { name: "About the Assessment" })).toHaveAttribute("href", "/#about");
    expect(screen.getByRole("link", { name: "Start Assessment" })).toHaveAttribute("href", "/assessment");
  });

  it("keeps the landing call to action and its target intentional", () => {
    render(<Home />);

    expect(screen.getByRole("link", { name: /Start Assessment/ })).toHaveAttribute("href", "/assessment");
    expect(screen.getByRole("link", { name: "How It Works" })).toHaveAttribute("href", "#how-it-works");
    expect(document.querySelector("#how-it-works")).toBeInTheDocument();
    expect(document.querySelector("#about")).toBeInTheDocument();
  });

  it("contains no dead or duplicate footer calls to action", () => {
    render(<SiteFooter />);
    const navigation = screen.getByRole("navigation", { name: "Footer navigation" });
    const links = within(navigation).getAllByRole("link");

    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      "/",
      "/assessment",
      "/#about",
    ]);
    expect(within(navigation).queryByText("Start Assessment")).not.toBeInTheDocument();
    expect(screen.queryByText(/MVP/i)).not.toBeInTheDocument();
    expect(document.querySelector('a[href="#"]')).not.toBeInTheDocument();
  });
});
