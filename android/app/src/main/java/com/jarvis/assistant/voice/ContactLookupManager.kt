package com.jarvis.assistant.voice

import android.content.Context
import android.database.Cursor
import android.provider.ContactsContract
import android.util.Log

/**
 * ContactLookupManager
 *
 * Resolves a contact name query to a phone number using Android's
 * ContactsContract.CommonDataKinds.Phone API.
 *
 * Flow:
 *   call mummy
 *     ↓
 *   Python backend → CONTACTS_LOOKUP payload { contact_query: "mummy" }
 *     ↓
 *   Android client calls ContactLookupManager.findContact("mummy")
 *     ↓
 *   Query ContactsContract.CommonDataKinds.Phone WHERE display_name LIKE '%mummy%'
 *     ↓
 *   Single match  → return ContactResult(name, phone)
 *   Multiple match → return first result (by display_name sort)
 *   No match      → return null
 *
 * Python backend NEVER dials names. Only numbers.
 *
 * Required permission: READ_CONTACTS (must be granted at runtime).
 */
object ContactLookupManager {

    private const val TAG = "ContactLookup"

    /**
     * Find a contact by name query.
     *
     * @param context  Android Context with READ_CONTACTS permission.
     * @param query    Name fragment to search for (case-insensitive).
     * @return         [ContactResult] with name + phone, or null if not found.
     */
    fun findContact(context: Context, query: String): ContactResult? {
        if (query.isBlank()) return null

        val uri = ContactsContract.CommonDataKinds.Phone.CONTENT_URI
        val projection = arrayOf(
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
            ContactsContract.CommonDataKinds.Phone.NUMBER,
            ContactsContract.CommonDataKinds.Phone.TYPE,
        )
        val selection = "${ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME} LIKE ?"
        val selectionArgs = arrayOf("%$query%")
        val sortOrder = "${ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME} ASC"

        var cursor: Cursor? = null
        try {
            cursor = context.contentResolver.query(
                uri, projection, selection, selectionArgs, sortOrder
            )

            if (cursor == null || !cursor.moveToFirst()) {
                Log.d(TAG, "No contact found for query: '$query'")
                return null
            }

            val nameIdx   = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
            val numberIdx = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.NUMBER)

            val name   = cursor.getString(nameIdx)   ?: return null
            val number = cursor.getString(numberIdx) ?: return null

            // Prefer mobile numbers if multiple rows (iterate to find TYPE_MOBILE)
            val mobile = findMobileNumber(cursor, nameIdx, numberIdx, name)

            val resolvedNumber = mobile ?: number.trim()
            Log.d(TAG, "Contact resolved: '$query' → '$name' [$resolvedNumber]")
            return ContactResult(name = name, phone = resolvedNumber)

        } catch (e: SecurityException) {
            Log.e(TAG, "READ_CONTACTS permission denied: ${e.message}")
            return null
        } catch (e: Exception) {
            Log.e(TAG, "ContactLookup error: ${e.message}", e)
            return null
        } finally {
            cursor?.close()
        }
    }

    /**
     * Scan remaining cursor rows to prefer mobile (TYPE_MOBILE) for the same contact name.
     */
    private fun findMobileNumber(
        cursor: Cursor,
        nameIdx: Int,
        numberIdx: Int,
        targetName: String,
    ): String? {
        val typeIdx = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.TYPE)
        // Rewind to first
        cursor.moveToFirst()
        do {
            val rowName = cursor.getString(nameIdx) ?: continue
            if (!rowName.equals(targetName, ignoreCase = true)) continue
            val rawNumber = cursor.getString(numberIdx) ?: continue
            val type = if (typeIdx >= 0) cursor.getInt(typeIdx) else -1
            if (type == ContactsContract.CommonDataKinds.Phone.TYPE_MOBILE) {
                return rawNumber.trim()
            }
        } while (cursor.moveToNext())
        return null
    }

    /**
     * Find all matching contacts for disambiguation (when multiple matches exist).
     *
     * @param context Android Context.
     * @param query   Name fragment.
     * @param limit   Max results to return.
     * @return List of [ContactResult].
     */
    fun findAllContacts(context: Context, query: String, limit: Int = 5): List<ContactResult> {
        if (query.isBlank()) return emptyList()

        val uri = ContactsContract.CommonDataKinds.Phone.CONTENT_URI
        val projection = arrayOf(
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
            ContactsContract.CommonDataKinds.Phone.NUMBER,
        )
        val selection = "${ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME} LIKE ?"
        val selectionArgs = arrayOf("%$query%")
        val sortOrder = "${ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME} ASC"

        val results = mutableListOf<ContactResult>()
        var cursor: Cursor? = null
        try {
            cursor = context.contentResolver.query(
                uri, projection, selection, selectionArgs, sortOrder
            ) ?: return emptyList()

            val nameIdx   = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
            val numberIdx = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.NUMBER)

            while (cursor.moveToNext() && results.size < limit) {
                val name   = cursor.getString(nameIdx)   ?: continue
                val number = cursor.getString(numberIdx) ?: continue
                if (results.none { it.name == name }) {   // deduplicate by name
                    results.add(ContactResult(name = name, phone = number.trim()))
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "findAllContacts error: ${e.message}", e)
        } finally {
            cursor?.close()
        }
        return results
    }
}

/**
 * Resolved contact information.
 *
 * @property name  Display name from ContactsContract.
 * @property phone Phone number (normalized, ready to dial).
 */
data class ContactResult(
    val name: String,
    val phone: String,
)
