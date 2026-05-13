import { defineStore } from 'pinia'
import { api } from '../api'

export const useWordBooksStore = defineStore('wordBooks', {
  state: () => ({
    allBooks: [],
    myBooks: [],
  }),
  getters: {
    activeBookIds: (state) => state.myBooks.map(b => b.id),
    activeBookNames: (state) => state.myBooks.map(b => b.name),
  },
  actions: {
    async fetchAllBooks() {
      const data = await api('word-books')
      this.allBooks = data.books
    },
    async fetchMyBooks() {
      const data = await api('word-books/my')
      this.myBooks = data.books
    },
    async activateBook(bookId) {
      await api(`word-books/${bookId}/activate`, { method: 'POST' })
      await this.fetchAllBooks()
      await this.fetchMyBooks()
    },
    async deactivateBook(bookId) {
      await api(`word-books/${bookId}/deactivate`, { method: 'POST' })
      await this.fetchAllBooks()
      await this.fetchMyBooks()
    },
  },
})
